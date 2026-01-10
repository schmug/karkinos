#!/usr/bin/env python3
"""Karkinos MCP Server - Expose worker management tools to Claude Code."""

import json
import re
import subprocess
import sys
from pathlib import Path


def validate_branch_name(branch: str) -> None:
    """Validate branch name to prevent argument injection."""
    if not branch:
        raise ValueError("Branch name cannot be empty")
    if branch.startswith("-"):
        raise ValueError(f"Invalid branch name '{branch}': cannot start with '-'")

    # Strict allow-list of characters to prevent argument injection and ensure valid git ref names.
    # Allowed: Alphanumeric, underscore, hyphen, dot, slash.
    # This automatically excludes space, ~, ^, :, ?, *, [, \, and control chars.
    if not re.match(r"^[a-zA-Z0-9/_.-]+$", branch):
        raise ValueError(f"Invalid branch name '{branch}': contains invalid characters")

    # Specific sequences banned by git or dangerous
    if ".." in branch:
        raise ValueError(f"Invalid branch name '{branch}': cannot contain '..'")

    if "//" in branch:
        raise ValueError(f"Invalid branch name '{branch}': cannot contain '//'")

    if branch.endswith("/") or branch.endswith("."):
        raise ValueError(f"Invalid branch name '{branch}': cannot end with '/' or '.'")

    if branch.startswith("/"):
        raise ValueError(f"Invalid branch name '{branch}': cannot start with '/'")

    if branch == "@":
        raise ValueError(f"Invalid branch name '{branch}': cannot be '@'")


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
    validate_branch_name(branch)
    if default_branch is None:
        default_branch = get_default_branch()

    # Git rev-list range syntax doesn't support -- separator easily,
    # but since we validate branch doesn't start with -, it's safe.
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
        # Ensure branch name is valid before passing to get_commits_ahead
        try:
            if branch != "detached":
                validate_branch_name(branch)
        except ValueError:
            # Skip invalid branch names in listing or treat as detached
            branch = "detached"

        workers.append(
            {
                "path": wt["path"],
                "name": Path(wt["path"]).name,
                "branch": branch,
                "commits_ahead": get_commits_ahead(branch, default_branch)
                if branch != "detached"
                else 0,
                "status": get_worktree_status(wt["path"]),
            }
        )

    return {"workers": workers, "count": len(workers)}


def get_worker_details(branch: str) -> dict:
    """Get detailed information about a specific worker."""
    validate_branch_name(branch)
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
            try:
                validate_branch_name(branch)
            except ValueError:
                # If branch name is invalid, we might skip it or log error
                # But here it comes from git worktree list, so it should be fine.
                # Still, defensive programming.
                continue

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
                    failed.append(
                        {"path": wt["path"], "branch": branch, "error": result.stderr.strip()}
                    )

    return {"cleaned": cleaned, "failed": failed, "dry_run": dry_run}


def update_branches(dry_run: bool = True, use_rebase: bool = True) -> dict:
    """Update worker branches by rebasing or merging main into them.

    Args:
        dry_run: If True, only report what would happen without making changes.
        use_rebase: If True, use rebase; if False, use merge.

    Returns:
        Dict with status for each worker branch.
    """
    # First fetch latest main
    fetch_result = subprocess.run(
        ["git", "fetch", "origin"],
        capture_output=True,
        text=True,
    )
    if fetch_result.returncode != 0:
        return {"error": f"Failed to fetch origin: {fetch_result.stderr.strip()}"}

    worktrees = get_worktrees()
    default_branch = get_default_branch()

    # Find main worktree path to exclude
    main_path = None
    for wt in worktrees:
        if wt.get("branch") == default_branch:
            main_path = wt["path"]
            break

    workers = [wt for wt in worktrees if wt["path"] != main_path and wt.get("branch")]

    results = {
        "updated": [],
        "already_up_to_date": [],
        "conflicts": [],
        "failed": [],
        "dry_run": dry_run,
        "method": "rebase" if use_rebase else "merge",
    }

    for wt in workers:
        branch = wt["branch"]
        path = wt["path"]

        try:
            validate_branch_name(branch)
        except ValueError:
            continue

        if not Path(path).exists():
            results["failed"].append(
                {
                    "branch": branch,
                    "path": path,
                    "error": "Worktree path does not exist",
                }
            )
            continue

        # Check if worktree has uncommitted changes
        status = get_worktree_status(path)
        if status == "modified":
            results["failed"].append(
                {
                    "branch": branch,
                    "path": path,
                    "error": "Worktree has uncommitted changes - commit or stash first",
                }
            )
            continue

        # Check if branch needs updating by comparing with origin/main
        # Use -- to separate options from args where possible
        merge_base_result = subprocess.run(
            ["git", "-C", path, "merge-base", branch, f"origin/{default_branch}"],
            capture_output=True,
            text=True,
        )

        origin_main_result = subprocess.run(
            ["git", "-C", path, "rev-parse", f"origin/{default_branch}"],
            capture_output=True,
            text=True,
        )

        if merge_base_result.returncode == 0 and origin_main_result.returncode == 0:
            merge_base = merge_base_result.stdout.strip()
            origin_main = origin_main_result.stdout.strip()

            if merge_base == origin_main:
                results["already_up_to_date"].append(
                    {
                        "branch": branch,
                        "path": path,
                    }
                )
                continue

        if dry_run:
            # In dry-run mode, simulate what would happen
            if use_rebase:
                # Check if rebase would have conflicts by doing a dry-run rebase
                subprocess.run(
                    [
                        "git",
                        "-C",
                        path,
                        "rebase",
                        "--no-autostash",
                        f"origin/{default_branch}",
                        "--dry-run",
                    ],
                    capture_output=True,
                    text=True,
                )
                # Note: git rebase doesn't have a true --dry-run, so we estimate
                # Just report it would be updated
                results["updated"].append(
                    {
                        "branch": branch,
                        "path": path,
                        "action": "would_rebase",
                    }
                )
            else:
                results["updated"].append(
                    {
                        "branch": branch,
                        "path": path,
                        "action": "would_merge",
                    }
                )
        else:
            # Actually perform the update
            if use_rebase:
                update_result = subprocess.run(
                    ["git", "-C", path, "rebase", f"origin/{default_branch}"],
                    capture_output=True,
                    text=True,
                )
            else:
                update_result = subprocess.run(
                    [
                        "git",
                        "-C",
                        path,
                        "merge",
                        f"origin/{default_branch}",
                        "-m",
                        f"Merge {default_branch} into {branch}",
                    ],
                    capture_output=True,
                    text=True,
                )

            if update_result.returncode == 0:
                results["updated"].append(
                    {
                        "branch": branch,
                        "path": path,
                        "action": "rebased" if use_rebase else "merged",
                    }
                )
            else:
                # Check if it's a conflict
                stderr = update_result.stderr.strip()
                stdout = update_result.stdout.strip()

                if "CONFLICT" in stderr or "CONFLICT" in stdout or "conflict" in stderr.lower():
                    # Abort the failed operation
                    if use_rebase:
                        subprocess.run(
                            ["git", "-C", path, "rebase", "--abort"], capture_output=True
                        )
                    else:
                        subprocess.run(["git", "-C", path, "merge", "--abort"], capture_output=True)

                    results["conflicts"].append(
                        {
                            "branch": branch,
                            "path": path,
                            "error": stderr or stdout,
                        }
                    )
                else:
                    results["failed"].append(
                        {
                            "branch": branch,
                            "path": path,
                            "error": stderr or stdout or "Unknown error",
                        }
                    )

    return results


def create_pr(branch: str, title: str, body: str = "", auto_merge: bool = True) -> dict:
    """Create a pull request for a worker branch.

    Args:
        branch: The git branch name to create PR for
        title: PR title
        body: PR description
        auto_merge: Enable auto-merge when CI passes (default: True)
    """
    try:
        validate_branch_name(branch)
    except ValueError as e:
        return {"error": str(e)}

    # First push the branch
    # Use -- to prevent argument injection
    push_result = subprocess.run(
        ["git", "push", "-u", "origin", "--", branch],
        capture_output=True,
        text=True,
    )

    if push_result.returncode != 0:
        return {"error": f"Failed to push branch: {push_result.stderr.strip()}"}

    # Create PR
    # Note: gh CLI might not support -- separator for --head argument in all versions,
    # but since we validated the branch name doesn't start with -, it is safe.
    pr_result = subprocess.run(
        [
            "gh",
            "pr",
            "create",
            "--head",
            branch,
            "--title",
            title,
            "--body",
            body or "Created by Karkinos",
        ],
        capture_output=True,
        text=True,
    )

    if pr_result.returncode != 0:
        return {"error": f"Failed to create PR: {pr_result.stderr.strip()}"}

    pr_url = pr_result.stdout.strip()

    # Enable auto-merge if requested
    auto_merge_result = None
    if auto_merge:
        # Extract PR number from URL (e.g., https://github.com/owner/repo/pull/123)
        pr_number = pr_url.rstrip("/").split("/")[-1]
        merge_result = subprocess.run(
            ["gh", "pr", "merge", pr_number, "--auto", "--squash"],
            capture_output=True,
            text=True,
        )
        if merge_result.returncode != 0:
            # Auto-merge may fail if repo doesn't have branch protection - that's OK
            auto_merge_result = {"enabled": False, "reason": merge_result.stderr.strip()}
        else:
            auto_merge_result = {"enabled": True}

    return {"success": True, "url": pr_url, "auto_merge": auto_merge_result}


def read_file(branch: str, file_path: str) -> dict:
    """Read a file from a worker worktree.

    Args:
        branch: Git branch name of the worker
        file_path: Path relative to worktree root

    Returns:
        Dict with file content or error message.
    """
    validate_branch_name(branch)
    worktrees = get_worktrees()

    # Find the worker by branch
    worker = None
    for wt in worktrees:
        if wt.get("branch") == branch:
            worker = wt
            break

    if not worker:
        return {"error": f"Worker with branch '{branch}' not found"}

    try:
        base_path = Path(worker["path"]).resolve()
        full_path = (base_path / file_path).resolve()

        # Security check: Ensure we haven't traversed outside the worktree
        # We use .parents to correctly handle sibling directory attacks
        if base_path not in full_path.parents and base_path != full_path:
            return {"error": f"Access denied: {file_path} is outside of worktree"}

    except Exception as e:
        return {"error": f"Invalid path: {str(e)}"}

    if not full_path.exists():
        return {"error": f"File not found: {file_path}"}

    if not full_path.is_file():
        return {"error": f"Not a file: {file_path}"}

    try:
        content = full_path.read_text()
        return {
            "branch": branch,
            "path": str(full_path),
            "relative_path": file_path,
            "content": content,
            "size": len(content),
        }
    except Exception as e:
        return {"error": f"Failed to read file: {str(e)}"}


def get_diff(branch: str, file_path: str | None = None) -> dict:
    """Get full diff for a worker branch compared to main.

    Args:
        branch: Git branch name of the worker
        file_path: Optional specific file to diff

    Returns:
        Dict with full diff content or error message.
    """
    validate_branch_name(branch)
    worktrees = get_worktrees()
    default_branch = get_default_branch()

    # Find the worker by branch
    worker = None
    for wt in worktrees:
        if wt.get("branch") == branch:
            worker = wt
            break

    if not worker:
        return {"error": f"Worker with branch '{branch}' not found"}

    path = worker["path"]

    cmd = ["git", "-C", path, "diff", f"{default_branch}...{branch}"]
    if file_path:
        cmd.append("--")
        cmd.append(file_path)

    diff_result = subprocess.run(cmd, capture_output=True, text=True)

    if diff_result.returncode != 0:
        return {"error": f"Failed to get diff: {diff_result.stderr.strip()}"}

    return {
        "branch": branch,
        "base": default_branch,
        "file_path": file_path,
        "diff": diff_result.stdout,
    }


# MCP Protocol Handler
def handle_request(request: dict) -> dict:
    """Handle MCP requests."""
    method = request.get("method", "")
    params = request.get("params", {})

    if method == "initialize":
        return {
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "karkinos", "version": "0.1.0"},
            }
        }

    elif method == "tools/list":
        return {
            "result": {
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
                            "properties": {
                                "branch": {
                                    "type": "string",
                                    "description": "The git branch name of the worker",
                                }
                            },
                            "required": ["branch"],
                        },
                    },
                    {
                        "name": "karkinos_cleanup_workers",
                        "description": "Remove merged or abandoned worker worktrees and their branches",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "dry_run": {
                                    "type": "boolean",
                                    "description": "Preview cleanup without making changes",
                                    "default": True,
                                }
                            },
                            "required": [],
                        },
                    },
                    {
                        "name": "karkinos_create_pr",
                        "description": "Create a pull request for a worker branch",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "branch": {
                                    "type": "string",
                                    "description": "The git branch name to create PR for",
                                },
                                "title": {"type": "string", "description": "PR title"},
                                "body": {"type": "string", "description": "PR description"},
                                "auto_merge": {
                                    "type": "boolean",
                                    "description": "Enable auto-merge when CI passes (default: true)",
                                    "default": True,
                                },
                            },
                            "required": ["branch", "title"],
                        },
                    },
                    {
                        "name": "karkinos_update_branches",
                        "description": "Update worker branches by rebasing or merging latest main into them. Use after merging a PR to prevent conflicts in other workers.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "dry_run": {
                                    "type": "boolean",
                                    "description": "Preview what would happen without making changes",
                                    "default": True,
                                },
                                "use_rebase": {
                                    "type": "boolean",
                                    "description": "Use rebase (True) or merge (False) to update branches",
                                    "default": True,
                                },
                            },
                            "required": [],
                        },
                    },
                    {
                        "name": "karkinos_read_file",
                        "description": "Read a file from a worker worktree",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "branch": {
                                    "type": "string",
                                    "description": "The git branch name of the worker",
                                },
                                "file_path": {
                                    "type": "string",
                                    "description": "Path relative to worktree root",
                                },
                            },
                            "required": ["branch", "file_path"],
                        },
                    },
                    {
                        "name": "karkinos_get_diff",
                        "description": "Get full diff content for a worker branch compared to main",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "branch": {
                                    "type": "string",
                                    "description": "The git branch name of the worker",
                                },
                                "file_path": {
                                    "type": "string",
                                    "description": "Optional: specific file to diff",
                                },
                            },
                            "required": ["branch"],
                        },
                    },
                ]
            }
        }

    elif method == "tools/call":
        tool_name = params.get("name", "")
        args = params.get("arguments", {})

        try:
            if tool_name == "karkinos_list_workers":
                result = list_workers()
            elif tool_name == "karkinos_get_worker_details":
                result = get_worker_details(args.get("branch", ""))
            elif tool_name == "karkinos_cleanup_workers":
                result = cleanup_workers(args.get("dry_run", True))
            elif tool_name == "karkinos_create_pr":
                result = create_pr(
                    args.get("branch", ""),
                    args.get("title", ""),
                    args.get("body", ""),
                    args.get("auto_merge", True),
                )
            elif tool_name == "karkinos_update_branches":
                result = update_branches(args.get("dry_run", True), args.get("use_rebase", True))
            elif tool_name == "karkinos_read_file":
                result = read_file(args.get("branch", ""), args.get("file_path", ""))
            elif tool_name == "karkinos_get_diff":
                result = get_diff(args.get("branch", ""), args.get("file_path"))
            else:
                result = {"error": f"Unknown tool: {tool_name}"}
        except ValueError as e:
            # Catch validation errors from validate_branch_name and others
            result = {"error": str(e)}

        return {"result": {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}}

    return {"error": {"code": -32601, "message": f"Unknown method: {method}"}}


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
