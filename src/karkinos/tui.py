"""Karkinos TUI - Monitor parallel Claude workers."""

import subprocess
from datetime import datetime
from pathlib import Path

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.reactive import reactive
from textual.widgets import DataTable, Footer, Header, Static
from textual.timer import Timer


class WorkerStatus(Static):
    """Widget showing summary status."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.worker_count = 0
        self.total_commits = 0

    def update_stats(self, workers: list[dict]):
        self.worker_count = len(workers)
        self.total_commits = sum(w.get("ahead", 0) for w in workers)
        self.refresh()

    def render(self) -> str:
        return (
            f"[bold cyan]Workers:[/] {self.worker_count}  "
            f"[bold green]Total Commits:[/] +{self.total_commits}  "
            f"[dim]Updated: {datetime.now().strftime('%H:%M:%S')}[/]"
        )


class WorkerTable(DataTable):
    """Table showing worker details."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.cursor_type = "row"
        self.zebra_stripes = True


class WorkerApp(App):
    """TUI application for monitoring Claude workers."""

    CSS = """
    Screen {
        background: $surface;
    }

    #status-bar {
        dock: top;
        height: 3;
        padding: 1;
        background: $primary-background;
    }

    #main-container {
        height: 100%;
        padding: 1;
    }

    WorkerTable {
        height: 100%;
    }

    #help-text {
        dock: bottom;
        height: 1;
        padding: 0 1;
        background: $primary-background;
        color: $text-muted;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("r", "refresh", "Refresh"),
        ("c", "cleanup", "Cleanup merged"),
        ("p", "create_pr", "Create PR"),
    ]

    worker_list: reactive[list[dict]] = reactive([])

    def __init__(self):
        super().__init__()
        self.refresh_timer: Timer | None = None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Container(
            WorkerStatus(id="status-bar"),
            WorkerTable(id="worker-table"),
            id="main-container",
        )
        yield Footer()

    def on_mount(self) -> None:
        """Set up the table and start refresh timer."""
        table = self.query_one(WorkerTable)
        table.add_columns("Worktree", "Branch", "Ahead", "Last Commit", "Status")

        self.refresh_workers()
        self.refresh_timer = self.set_interval(5, self.refresh_workers)

    def get_worktrees(self) -> list[dict]:
        """Get list of git worktrees with status."""
        result = subprocess.run(
            ["git", "worktree", "list", "--porcelain"],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            return []

        worktrees = []
        current = {}

        for line in result.stdout.strip().split("\n"):
            if line.startswith("worktree "):
                if current:
                    worktrees.append(current)
                current = {"path": line[9:]}
            elif line.startswith("HEAD "):
                current["head"] = line[5:]
            elif line.startswith("branch "):
                current["branch"] = line[7:].replace("refs/heads/", "")
            elif line == "detached":
                current["detached"] = True

        if current:
            worktrees.append(current)

        return worktrees

    def get_worker_details(self, wt: dict) -> dict:
        """Enrich worktree with additional details."""
        branch = wt.get("branch", "")

        # Commits ahead of main
        result = subprocess.run(
            ["git", "rev-list", "--count", f"main..{branch}"],
            capture_output=True,
            text=True,
        )
        wt["ahead"] = int(result.stdout.strip()) if result.returncode == 0 else 0

        # Last commit
        result = subprocess.run(
            ["git", "log", branch, "--oneline", "-1", "--format=%s"],
            capture_output=True,
            text=True,
        )
        wt["last_commit"] = result.stdout.strip()[:50] if result.returncode == 0 else ""

        # Status
        if not Path(wt["path"]).exists():
            wt["status"] = "missing"
        else:
            result = subprocess.run(
                ["git", "-C", wt["path"], "status", "--porcelain"],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                wt["status"] = "modified" if result.stdout.strip() else "clean"
            else:
                wt["status"] = "unknown"

        return wt

    def refresh_workers(self) -> None:
        """Refresh the worker list."""
        worktrees = self.get_worktrees()

        # Find main to exclude
        main_path = None
        for wt in worktrees:
            if wt.get("branch") in ("main", "master"):
                main_path = wt["path"]
                break

        # Get workers with details
        workers = []
        for wt in worktrees:
            if wt["path"] != main_path and not wt.get("detached"):
                workers.append(self.get_worker_details(wt))

        self.worker_list = workers

        # Update table
        table = self.query_one(WorkerTable)
        table.clear()

        for w in workers:
            path = Path(w["path"]).name
            branch = w.get("branch", "?")
            ahead = f"+{w.get('ahead', 0)}"
            commit = w.get("last_commit", "")[:40]
            status = w.get("status", "?")

            # Color status
            if status == "clean":
                status = "[green]clean[/]"
            elif status == "modified":
                status = "[yellow]modified[/]"
            elif status == "missing":
                status = "[red]missing[/]"

            table.add_row(path, branch, ahead, commit, status)

        # Update status bar
        status_bar = self.query_one(WorkerStatus)
        status_bar.update_stats(workers)

    def action_refresh(self) -> None:
        """Manual refresh."""
        self.refresh_workers()
        self.notify("Refreshed")

    def action_cleanup(self) -> None:
        """Clean up merged worktrees."""
        result = subprocess.run(
            ["git", "branch", "--merged", "main"],
            capture_output=True,
            text=True,
        )
        merged = set(b.strip() for b in result.stdout.strip().split("\n"))

        cleaned = 0
        for w in self.worker_list:
            branch = w.get("branch")
            if branch and branch in merged:
                subprocess.run(["git", "worktree", "remove", w["path"]])
                subprocess.run(["git", "branch", "-d", branch])
                cleaned += 1

        self.refresh_workers()
        self.notify(f"Cleaned {cleaned} worktree(s)")

    def action_create_pr(self) -> None:
        """Create PR for selected worker."""
        table = self.query_one(WorkerTable)
        if table.cursor_row is not None and self.worker_list:
            worker = self.worker_list[table.cursor_row]
            branch = worker.get("branch")
            if branch:
                # Would need to be async in real implementation
                self.notify(f"Would create PR for {branch}")


def main():
    app = WorkerApp()
    app.run()


if __name__ == "__main__":
    main()
