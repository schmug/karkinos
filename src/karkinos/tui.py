"""Karkinos TUI - Monitor parallel Claude workers."""

import subprocess
from datetime import datetime
from pathlib import Path

from textual.app import App, ComposeResult
from textual.containers import Container
from textual.reactive import reactive
from textual.timer import Timer
from textual.widgets import DataTable, Footer, Header, Static


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

    #empty-state {
        display: none;
        text-align: center;
        padding: 2;
        color: $text-muted;
        height: 100%;
        content-align: center middle;
    }

    .empty #worker-table {
        display: none;
    }

    .empty #empty-state {
        display: block;
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
            Static(
                "No active workers.\n\nUse /worker in Claude to start one.",
                id="empty-state",
            ),
            id="main-container",
        )
        yield Footer()

    def on_mount(self) -> None:
        """Set up the table and start refresh timer."""
        table = self.query_one(WorkerTable)
        table.add_columns("Worktree", "Branch", "Ahead", "Last Commit", "Status")

        self.refresh_workers()
        self.refresh_timer = self.set_interval(5, self.refresh_workers)

    def on_unmount(self) -> None:
        """Cancel refresh timer on shutdown."""
        if self.refresh_timer:
            self.refresh_timer.stop()

    def get_worktrees(self) -> list[dict]:
        """Get list of git worktrees with status."""
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
                if current and "path" in current:
                    worktrees.append(current)
                current = {"path": line[9:]}
            elif line.startswith("HEAD "):
                current["head"] = line[5:]
            elif line.startswith("branch "):
                current["branch"] = line[7:].replace("refs/heads/", "")
            elif line == "detached":
                current["detached"] = True

        if current and "path" in current:
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
        if result.returncode == 0:
            try:
                wt["ahead"] = int(result.stdout.strip())
            except ValueError:
                wt["ahead"] = 0
        else:
            wt["ahead"] = 0

        # Last commit
        result = subprocess.run(
            ["git", "log", branch, "--oneline", "-1", "--format=%s"],
            capture_output=True,
            text=True,
        )
        wt["last_commit"] = result.stdout.strip()[:50] if result.returncode == 0 else ""

        # Status
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
        container = self.query_one("#main-container")
        table.clear()

        if not workers:
            container.add_class("empty")
        else:
            container.remove_class("empty")

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
        if result.returncode != 0:
            self.notify("Failed to get merged branches", severity="error")
            return
        merged = set(b.strip() for b in result.stdout.strip().split("\n"))

        cleaned = 0
        for w in self.worker_list:
            branch = w.get("branch")
            if branch and branch in merged:
                result = subprocess.run(
                    ["git", "worktree", "remove", w["path"]],
                    capture_output=True,
                    text=True,
                )
                if result.returncode != 0:
                    self.notify(f"Failed to remove worktree: {w['path']}", severity="warning")
                    continue

                result = subprocess.run(
                    ["git", "branch", "-d", branch],
                    capture_output=True,
                    text=True,
                )
                if result.returncode != 0:
                    self.notify(f"Failed to delete branch: {branch}", severity="warning")
                    continue

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
