#!/usr/bin/env python3
"""Karkinos CLI - manage parallel Claude workers."""

import argparse
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


def get_commits_ahead(branch: str) -> int:
    """Get number of commits ahead of main."""
    result = subprocess.run(
        ["git", "rev-list", "--count", f"main..{branch}"],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        try:
            return int(result.stdout.strip())
        except ValueError:
            return 0
    return 0


def get_last_commit(branch: str) -> str:
    """Get last commit message for a branch."""
    result = subprocess.run(
        ["git", "log", branch, "--oneline", "-1"],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        return result.stdout.strip()
    return ""


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


def cmd_list(args):
    """List all active workers."""
    worktrees = get_worktrees()

    if not worktrees:
        print("No worktrees found.")
        return

    # Find main worktree to exclude
    main_path = None
    for wt in worktrees:
        if wt.get("branch") in ("main", "master"):
            main_path = wt["path"]
            break

    workers = [wt for wt in worktrees if wt["path"] != main_path]

    if not workers:
        print("No active workers. Main worktree only.")
        return

    print(f"\n{'Worktree':<30} {'Branch':<35} {'Ahead':<6} {'Status':<10}")
    print("-" * 85)

    for wt in workers:
        path = Path(wt["path"]).name
        branch = wt.get("branch", "detached")
        ahead = get_commits_ahead(branch) if branch != "detached" else 0
        status = get_worktree_status(wt["path"])

        print(f"{path:<30} {branch:<35} +{ahead:<5} {status:<10}")

    print()


def cmd_watch(args):
    """Launch TUI to watch workers."""
    if args.simple:
        simple_watch()
    else:
        from karkinos.tui import WorkerApp

        app = WorkerApp()
        app.run()


def simple_watch():
    """Simple text-based watch loop (no TUI, safe for shared terminals)."""
    import time

    try:
        while True:
            # Clear screen and move cursor to top
            print("\033[2J\033[H", end="")
            print(f"Karkinos Workers - {time.strftime('%H:%M:%S')}  (Ctrl+C to exit)")
            print("-" * 85)

            worktrees = get_worktrees()

            # Find main worktree to exclude
            main_path = None
            for wt in worktrees:
                if wt.get("branch") in ("main", "master"):
                    main_path = wt["path"]
                    break

            workers = [wt for wt in worktrees if wt["path"] != main_path and not wt.get("detached")]

            if not workers:
                print("No active workers.")
            else:
                print(f"{'Worktree':<30} {'Branch':<35} {'Ahead':<6} {'Status':<10}")
                print("-" * 85)

                for wt in workers:
                    path = Path(wt["path"]).name
                    branch = wt.get("branch", "detached")
                    ahead = get_commits_ahead(branch) if branch != "detached" else 0
                    status = get_worktree_status(wt["path"])
                    print(f"{path:<30} {branch:<35} +{ahead:<5} {status:<10}")

            print("\nRefreshing every 5 seconds...")
            time.sleep(5)
    except KeyboardInterrupt:
        print("\nStopped.")


def cmd_init(args):
    """Initialize karkinos in a project."""
    import shutil
    from importlib.resources import as_file, files

    claude_dir = Path(".claude")
    skills_dir = claude_dir / "skills"
    commands_dir = claude_dir / "commands"

    # Access bundled data from package
    try:
        data_pkg = files("karkinos.data")
    except ModuleNotFoundError:
        print("Error: Could not find karkinos data package.")
        print("Try reinstalling: uv tool install karkinos --force")
        sys.exit(1)

    # Create directories
    skills_dir.mkdir(parents=True, exist_ok=True)
    commands_dir.mkdir(parents=True, exist_ok=True)

    # Copy skills
    with as_file(data_pkg / "skills") as src_skills:
        if not src_skills.exists():
            print("Error: Could not find skills in package.")
            sys.exit(1)
        for skill in src_skills.iterdir():
            if skill.is_dir():
                dest = skills_dir / skill.name
                if dest.exists():
                    print(f"  Skipping {skill.name} (exists)")
                else:
                    shutil.copytree(skill, dest)
                    print(f"  Added skill: {skill.name}")

    # Copy commands
    with as_file(data_pkg / "commands") as src_commands:
        if not src_commands.exists():
            print("Error: Could not find commands in package.")
            sys.exit(1)
        for cmd in src_commands.iterdir():
            if cmd.is_file() and cmd.suffix == ".md":
                dest = commands_dir / cmd.name
                if dest.exists():
                    print(f"  Skipping {cmd.name} (exists)")
                else:
                    shutil.copy(cmd, dest)
                    print(f"  Added command: {cmd.name}")

    print("\nKarkinos initialized! Available commands:")
    print("  /worker, /issue-worker, /pr-worker, /workers, /worker-cleanup")
    print("\nRun 'karkinos watch' in another terminal to monitor workers.")


def cmd_cleanup(args):
    """Clean up merged worktrees."""
    worktrees = get_worktrees()

    # Find main
    main_path = None
    for wt in worktrees:
        if wt.get("branch") in ("main", "master"):
            main_path = wt["path"]
            break

    workers = [wt for wt in worktrees if wt["path"] != main_path]

    if not workers:
        print("No workers to clean up.")
        return

    # Check which are merged
    result = subprocess.run(
        ["git", "branch", "--merged", "main"],
        capture_output=True,
        text=True,
    )
    output = result.stdout.strip()
    merged = set(b.strip() for b in output.split("\n")) if output else set()

    cleaned = 0
    for wt in workers:
        branch = wt.get("branch")
        if branch and branch in merged:
            if args.dry_run:
                print(f"Would remove: {wt['path']} ({branch})")
            else:
                result = subprocess.run(
                    ["git", "worktree", "remove", wt["path"]],
                    capture_output=True,
                    text=True,
                )
                if result.returncode != 0:
                    print(f"Warning: Failed to remove worktree {wt['path']}")
                    if result.stderr:
                        print(f"  {result.stderr.strip()}")
                    continue
                # Only delete branch if worktree removal succeeded
                result = subprocess.run(
                    ["git", "branch", "-d", branch],
                    capture_output=True,
                    text=True,
                )
                if result.returncode != 0:
                    print(f"Warning: Failed to delete branch {branch}")
                    if result.stderr:
                        print(f"  {result.stderr.strip()}")
                else:
                    print(f"Removed: {wt['path']} ({branch})")
            cleaned += 1

    if cleaned == 0:
        print("No merged worktrees to clean up.")
    elif args.dry_run:
        print(f"\nWould clean {cleaned} worktree(s). Run without --dry-run to apply.")


def main():
    parser = argparse.ArgumentParser(
        description="Karkinos - Parallel Claude Code workers",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  karkinos list          List active workers
  karkinos watch         Launch TUI monitor
  karkinos init          Add skills/commands to current project
  karkinos cleanup       Remove merged worktrees
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # list
    list_parser = subparsers.add_parser("list", help="List active workers")
    list_parser.set_defaults(func=cmd_list)

    # watch
    watch_parser = subparsers.add_parser("watch", help="Launch TUI monitor")
    watch_parser.add_argument(
        "--simple",
        "-s",
        action="store_true",
        help="Simple text output (no TUI, safe for shared terminals)",
    )
    watch_parser.set_defaults(func=cmd_watch)

    # init
    init_parser = subparsers.add_parser("init", help="Initialize in current project")
    init_parser.set_defaults(func=cmd_init)

    # cleanup
    cleanup_parser = subparsers.add_parser("cleanup", help="Remove merged worktrees")
    cleanup_parser.add_argument("--dry-run", action="store_true", help="Show what would be removed")
    cleanup_parser.set_defaults(func=cmd_cleanup)

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    args.func(args)


if __name__ == "__main__":
    main()
