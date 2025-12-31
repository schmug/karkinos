#!/usr/bin/env python3
"""Karkinos MCP Server - Expose worker management tools to Claude Code."""

import json
import subprocess
import sys
from pathlib import Path


def get_worktrees() -> list[dict]:
    """Get list of git worktrees with their status."""
    result = subprocess.run(
        ["git", "worktree", "list", "--porcelain"],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        return []

    output = result.stdout.strip()
    if not output:
        return []

    worktrees = []
    current = {}

    for line in output.split("\n"):
        if line.startswith("worktree "):
            if current:
                worktrees.append(current)
            current = {"path": line[9:]}
        elif line.startswith("HEAD "):
            current["head"] = line[5:]
        elif line.startswith("branch "):
            current["branch"] = line[7:].replace("refs/heads/", "")
        elif line == "bare":
            current["bare"] = True
        elif line == "detached":
            current["detached"] = True

    if current:
        worktrees.append(current)

    return worktrees


def get_default_branch() -> str:
    """Detect the default branch dynamically."""
    result = subprocess.run(
        ["git", "symbolic-ref", "refs/remotes/origin/HEAD"],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        return result.stdout.strip().replace("refs/remotes/origin/", "")
    return "main"


def get_commits_ahead(branch: str, default_branch: str | None = None) -> int:
    """Get number of commits ahead of default branch."""
    if default_branch is None:
        default_branch = get_default_branch()
    result = subprocess.run(
        ["git", "rev-list", "--count", f"{default_branch}..{branch}"],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        try:
            return int(result.stdout.strip())
        except ValueError:
            return 0
    return 0


def get_worktree_status(path: str) -> str:
    """Check if worktree has uncommitted changes."""
    if not Path(path).exists():
        return "missing"
    result = subprocess.run(
        ["git", "-C", path, "status", "--porcelain"],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        if result.stdout.strip():
            return "modified"
        return "clean"
    return "unknown"


def list_workers() -> dict:
    """List all active workers with status."""
    worktrees = get_worktrees()
    default_branch = get_default_branch()

    # Find main worktree to exclude
    main_path = None
    for wt in worktrees:
        if wt.get("branch") == default_branch:
            main_path = wt["path"]
            break

    workers = []
    for wt in worktrees:
        if wt["path"] == main_path:
            continue

        branch = wt.get("branch", "detached")
        workers.append({
            "path": wt["path"],
            "name": Path(wt["path"]).name,
            "branch": branch,
            "commits_ahead": get_commits_ahead(branch, default_branch) if branch != "detached" else 0,
            "status": get_worktree_status(wt["path"]),
        })

    return {"workers": workers, "count": len(workers)}


def get_worker_details(branch: str) -> dict:
    """Get detailed information about a specific worker."""
    worktrees = get_worktrees()
    default_branch = get_default_branch()

    # Find the worker
    worker = None
    for wt in worktrees:
        if wt.get("branch") == branch:
            worker = wt
            break

    if not worker:
        return {"error": f"Worker with branch '{branch}' not found"}

    path = worker["path"]

    # Get commits
    commits_result = subprocess.run(
        ["git", "-C", path, "log", f"{default_branch}..{branch}", "--oneline"],
        capture_output=True,
        text=True,
    )
    commits = commits_result.stdout.strip().split("\n") if commits_result.stdout.strip() else []

    # Get diff stats
    diff_result = subprocess.run(
        ["git", "-C", path, "diff", f"{default_branch}...{branch}", "--stat"],
        capture_output=True,
        text=True,
    )

    return {
        "branch": branch,
        "path": path,
        "name": Path(path).name,
        "status": get_worktree_status(path),
        "commits_ahead": len(commits),
        "commits": commits,
        "diff_stat": diff_result.stdout.strip(),
    }


def cleanup_workers(dry_run: bool = True) -> dict:
    """Remove merged worktrees and their branches."""
    worktrees = get_worktrees()
    default_branch = get_default_branch()

    # Find main
    main_path = None
    for wt in worktrees:
        if wt.get("branch") == default_branch:
            main_path = wt["path"]
            break

    workers = [wt for wt in worktrees if wt["path"] != main_path]

    # Get merged branches
    result = subprocess.run(
        ["git", "branch", "--merged", default_branch],
        capture_output=True,
        text=True,
    )
    output = result.stdout.strip()
    merged = set(b.strip() for b in output.split("\n")) if output else set()

    cleaned = []
    failed = []

    for wt in workers:
        branch = wt.get("branch")
        if branch and branch in merged:
            if dry_run:
                cleaned.append({"path": wt["path"], "branch": branch, "action": "would_remove"})
            else:
                # Actually remove
                result = subprocess.run(
                    ["git", "worktree", "remove", wt["path"]],
                    capture_output=True,
                    text=True,
                )
                if result.returncode == 0:
                    subprocess.run(["git", "branch", "-d", branch], capture_output=True)
                    cleaned.append({"path": wt["path"], "branch": branch, "action": "removed"})
                else:
                    failed.append({"path": wt["path"], "branch": branch, "error": result.stderr.strip()})

    return {"cleaned": cleaned, "failed": failed, "dry_run": dry_run}


def create_pr(branch: str, title: str, body: str = "") -> dict:
    """Create a pull request for a worker branch."""
    # First push the branch
    push_result = subprocess.run(
        ["git", "push", "-u", "origin", branch],
        capture_output=True,
        text=True,
    )

    if push_result.returncode != 0:
        return {"error": f"Failed to push branch: {push_result.stderr.strip()}"}

    # Create PR
    pr_result = subprocess.run(
        ["gh", "pr", "create", "--head", branch, "--title", title, "--body", body or "Created by Karkinos"],
        capture_output=True,
        text=True,
    )

    if pr_result.returncode != 0:
        return {"error": f"Failed to create PR: {pr_result.stderr.strip()}"}

    return {"success": True, "url": pr_result.stdout.strip()}


# MCP Protocol Handler
def handle_request(request: dict) -> dict:
    """Handle MCP requests."""
    method = request.get("method", "")
    params = request.get("params", {})

    if method == "initialize":
        return {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "karkinos", "version": "0.1.0"},
        }

    elif method == "tools/list":
        return {
            "tools": [
                {
                    "name": "karkinos_list_workers",
                    "description": "List all active git worktrees with status (branch, commits ahead, clean/modified)",
                    "inputSchema": {"type": "object", "properties": {}, "required": []},
                },
                {
                    "name": "karkinos_get_worker_details",
                    "description": "Get detailed information about a specific worker including commits and diff stats",
                    "inputSchema": {
                        "type": "object",
                        "properties": {"branch": {"type": "string", "description": "The git branch name of the worker"}},
                        "required": ["branch"],
                    },
                },
                {
                    "name": "karkinos_cleanup_workers",
                    "description": "Remove merged or abandoned worker worktrees and their branches",
                    "inputSchema": {
                        "type": "object",
                        "properties": {"dry_run": {"type": "boolean", "description": "Preview cleanup without making changes", "default": True}},
                        "required": [],
                    },
                },
                {
                    "name": "karkinos_create_pr",
                    "description": "Create a pull request for a worker branch",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "branch": {"type": "string", "description": "The git branch name to create PR for"},
                            "title": {"type": "string", "description": "PR title"},
                            "body": {"type": "string", "description": "PR description"},
                        },
                        "required": ["branch", "title"],
                    },
                },
            ]
        }

    elif method == "tools/call":
        tool_name = params.get("name", "")
        args = params.get("arguments", {})

        if tool_name == "karkinos_list_workers":
            result = list_workers()
        elif tool_name == "karkinos_get_worker_details":
            result = get_worker_details(args.get("branch", ""))
        elif tool_name == "karkinos_cleanup_workers":
            result = cleanup_workers(args.get("dry_run", True))
        elif tool_name == "karkinos_create_pr":
            result = create_pr(args.get("branch", ""), args.get("title", ""), args.get("body", ""))
        else:
            result = {"error": f"Unknown tool: {tool_name}"}

        return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}

    return {"error": f"Unknown method: {method}"}


def main():
    """Main MCP server loop using stdio."""
    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break

            request = json.loads(line)
            response = handle_request(request)
            response["jsonrpc"] = "2.0"
            response["id"] = request.get("id")

            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()

        except json.JSONDecodeError:
            continue
        except Exception as e:
            error_response = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32603, "message": str(e)},
            }
            sys.stdout.write(json.dumps(error_response) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
