"""Karkinos TUI - Monitor parallel Claude workers."""

import subprocess
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

from textual import work
from textual.app import App, ComposeResult
from textual.containers import Container, ScrollableContainer, Vertical
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual.timer import Timer
from textual.widgets import DataTable, Footer, Static


def get_default_branch() -> str:
    """Detect the default branch dynamically from remote HEAD."""
    result = subprocess.run(
        ["git", "symbolic-ref", "refs/remotes/origin/HEAD"],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        return result.stdout.strip().replace("refs/remotes/origin/", "")
    return "main"  # fallback


class WorkerDetailScreen(ModalScreen):
    """Modal screen showing worker details (logs, diff, info)."""

    CSS = """
    WorkerDetailScreen {
        align: center middle;
    }

    #detail-container {
        width: 90%;
        height: 90%;
        background: $surface;
        border: thick $primary;
        padding: 1 2;
    }

    #detail-header {
        height: 3;
        background: $primary-background;
        padding: 0 1;
        margin-bottom: 1;
    }

    #detail-content {
        height: 1fr;
        overflow-y: auto;
        padding: 0 1;
    }

    #detail-footer {
        height: 1;
        dock: bottom;
        background: $primary-background;
        color: $text-muted;
        padding: 0 1;
    }
    """

    BINDINGS = [
        ("escape", "dismiss", "Close"),
        ("q", "dismiss", "Close"),
        ("l", "show_logs", "Logs"),
        ("d", "show_diff", "Diff"),
        ("i", "show_info", "Info"),
    ]

    def __init__(self, worker: dict, view: str = "info"):
        super().__init__()
        self.worker = worker
        self.current_view = view

    def compose(self) -> ComposeResult:
        with Vertical(id="detail-container"):
            yield Static(id="detail-header")
            yield ScrollableContainer(Static(id="detail-text"), id="detail-content")
            yield Static("[l] Logs  [d] Diff  [i] Info  [ESC/q] Close", id="detail-footer")

    def on_mount(self) -> None:
        self._update_view()

    def _update_view(self) -> None:
        """Update the display based on current view."""
        header = self.query_one("#detail-header", Static)
        content = self.query_one("#detail-text", Static)

        branch = self.worker.get("branch", "unknown")

        if self.current_view == "logs":
            header.update(f"[bold cyan]Commit Log:[/] {branch}")
            content.update(self._get_logs())
        elif self.current_view == "diff":
            header.update(f"[bold cyan]Diff vs {get_default_branch()}:[/] {branch}")
            content.update(self._get_diff())
        else:  # info
            header.update(f"[bold cyan]Worker Info:[/] {branch}")
            content.update(self._get_info())

    def _get_logs(self) -> str:
        """Get commit log for the worker branch."""
        branch = self.worker.get("branch", "")
        default_branch = get_default_branch()

        result = subprocess.run(
            [
                "git",
                "log",
                f"{default_branch}..{branch}",
                "--format=%C(yellow)%h%C(reset) %C(green)%ar%C(reset) %s%n%C(dim)%an%C(reset)%n",
            ],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0 or not result.stdout.strip():
            return "[dim]No commits ahead of default branch[/]"

        return result.stdout.strip()

    def _get_diff(self) -> str:
        """Get diff for the worker branch vs default branch."""
        branch = self.worker.get("branch", "")
        default_branch = get_default_branch()

        result = subprocess.run(
            ["git", "diff", f"{default_branch}...{branch}", "--stat"],
            capture_output=True,
            text=True,
        )

        stat_output = result.stdout.strip() if result.returncode == 0 else ""

        result = subprocess.run(
            ["git", "diff", f"{default_branch}...{branch}"],
            capture_output=True,
            text=True,
        )

        diff_output = result.stdout.strip() if result.returncode == 0 else ""

        if not stat_output and not diff_output:
            return "[dim]No changes vs default branch[/]"

        # Colorize diff output
        lines = []
        if stat_output:
            lines.append("[bold]File Summary:[/]")
            lines.append(stat_output)
            lines.append("")
            lines.append("[bold]Diff:[/]")

        for line in diff_output.split("\n"):
            if line.startswith("+") and not line.startswith("+++"):
                lines.append(f"[green]{line}[/]")
            elif line.startswith("-") and not line.startswith("---"):
                lines.append(f"[red]{line}[/]")
            elif line.startswith("@@"):
                lines.append(f"[cyan]{line}[/]")
            elif line.startswith("diff "):
                lines.append(f"[bold yellow]{line}[/]")
            else:
                lines.append(line)

        return "\n".join(lines)

    def _get_info(self) -> str:
        """Get detailed info about the worker."""
        branch = self.worker.get("branch", "unknown")
        path = self.worker.get("path", "unknown")
        status = self.worker.get("status", "unknown")
        ahead = self.worker.get("ahead", 0)
        default_branch = get_default_branch()

        lines = [
            f"[bold]Branch:[/] {branch}",
            f"[bold]Path:[/] {path}",
            f"[bold]Status:[/] {status}",
            f"[bold]Commits ahead of {default_branch}:[/] +{ahead}",
            "",
        ]

        # Get files changed
        result = subprocess.run(
            ["git", "diff", f"{default_branch}...{branch}", "--name-status"],
            capture_output=True,
            text=True,
        )

        if result.returncode == 0 and result.stdout.strip():
            lines.append("[bold]Changed Files:[/]")
            for file_line in result.stdout.strip().split("\n"):
                parts = file_line.split("\t", 1)
                if len(parts) == 2:
                    status_char, filename = parts
                    if status_char == "A":
                        lines.append(f"  [green]+ {filename}[/]")
                    elif status_char == "D":
                        lines.append(f"  [red]- {filename}[/]")
                    elif status_char == "M":
                        lines.append(f"  [yellow]~ {filename}[/]")
                    else:
                        lines.append(f"  {status_char} {filename}")
        else:
            lines.append("[dim]No changed files[/]")

        lines.append("")

        # Get recent commits
        result = subprocess.run(
            [
                "git",
                "log",
                f"{default_branch}..{branch}",
                "--oneline",
                "-10",
            ],
            capture_output=True,
            text=True,
        )

        if result.returncode == 0 and result.stdout.strip():
            lines.append("[bold]Recent Commits:[/]")
            for commit_line in result.stdout.strip().split("\n"):
                lines.append(f"  [yellow]{commit_line}[/]")
        else:
            lines.append("[dim]No commits ahead of default branch[/]")

        return "\n".join(lines)

    def action_show_logs(self) -> None:
        """Switch to logs view."""
        self.current_view = "logs"
        self._update_view()

    def action_show_diff(self) -> None:
        """Switch to diff view."""
        self.current_view = "diff"
        self._update_view()

    def action_show_info(self) -> None:
        """Switch to info view."""
        self.current_view = "info"
        self._update_view()


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


class CrabHeader(Static):
    """ASCII crab header for Karkinos with animated eyes."""

    # Animation frames: (claws, eyes)
    FRAMES = [
        ("(\\/)", "(°°)"),  # Open eyes, claws up
        ("(\\/)", "(••)"),  # Blink
        ("(\\/)", "(°°)"),  # Open eyes
        ("(\\\\)", "(°°)"),  # Claws move left
        ("(\\/)", "(°°)"),  # Claws back
        ("(//)", "(°°)"),  # Claws move right
    ]

    frame_index: reactive[int] = reactive(0)

    def on_mount(self) -> None:
        """Start the animation timer."""
        self.set_interval(1.5, self._next_frame)

    def _next_frame(self) -> None:
        """Advance to the next animation frame."""
        self.frame_index = (self.frame_index + 1) % len(self.FRAMES)

    def watch_frame_index(self) -> None:
        """React to frame changes by refreshing the display."""
        self.refresh()

    def render(self) -> str:
        claws, eyes = self.FRAMES[self.frame_index]
        return (
            f"[bold orange1]{claws} [cyan]KARKINOS[/cyan] {claws}  "
            f"[bold cyan]Worker Monitor[/bold cyan]  "
            f"[bold orange1]{eyes}[/bold orange1]"
        )


class WorkerApp(App):
    """TUI application for monitoring Claude workers."""

    TITLE = "🦀 Karkinos"

    CSS = """
    Screen {
        background: $surface;
    }

    CrabHeader {
        dock: top;
        height: 1;
        padding: 0 1;
        background: $primary-background;
        text-align: center;
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
        ("enter", "show_details", "Details"),
        ("l", "show_logs", "Logs"),
        ("d", "show_diff", "Diff"),
    ]

    worker_list: reactive[list[dict]] = reactive([])

    def __init__(self):
        super().__init__()
        self.refresh_timer: Timer | None = None

    def compose(self) -> ComposeResult:
        yield CrabHeader()
        yield Container(
            WorkerStatus(id="status-bar"),
            WorkerTable(id="worker-table"),
            id="main-container",
        )
        yield Footer()

    def on_mount(self) -> None:
        """Set up the table and start refresh timer."""
        table = self.query_one(WorkerTable)
        table.add_columns("Worktree", "Branch", "Ahead", "Last Commit", "Activity", "Status")

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

    def get_all_branch_commits(self) -> dict[str, str]:
        """Batch fetch all branch commit messages in one git call."""
        result = subprocess.run(
            ["git", "for-each-ref", "--format=%(refname:short)|%(subject)", "refs/heads/"],
            capture_output=True,
            text=True,
        )
        commits = {}
        if result.returncode == 0:
            for line in result.stdout.strip().split("\n"):
                if "|" in line:
                    branch, msg = line.split("|", 1)
                    commits[branch] = msg
        return commits

    def get_worker_details(
        self, wt: dict, default_branch: str, branch_commits: dict[str, str]
    ) -> dict:
        """Enrich worktree with additional details."""
        branch = wt.get("branch", "")

        # Commits ahead of default branch
        result = subprocess.run(
            ["git", "rev-list", "--count", f"{default_branch}..{branch}"],
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

        # Last commit (from pre-fetched batch)
        wt["last_commit"] = branch_commits.get(branch, "")[:50]

        # Status and activity
        if not Path(wt["path"]).exists():
            wt["status"] = "missing"
            wt["activity"] = ""
        else:
            result = subprocess.run(
                ["git", "-C", wt["path"], "status", "--porcelain"],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                status_output = result.stdout.strip()
                wt["status"] = "modified" if status_output else "clean"
                # Extract activity from first changed file
                if status_output:
                    first_line = status_output.split("\n")[0]
                    # Format: "XY filename" where XY is the status code
                    wt["activity"] = first_line[:30]
                else:
                    wt["activity"] = "idle"
            else:
                wt["status"] = "unknown"
                wt["activity"] = ""

        return wt

    @work(thread=True, exclusive=True)
    def refresh_workers(self) -> None:
        """Refresh the worker list in a background thread."""
        worktrees = self.get_worktrees()

        # Find default branch to exclude
        default_branch = get_default_branch()
        main_path = None
        for wt in worktrees:
            if wt.get("branch") == default_branch:
                main_path = wt["path"]
                break

        # Batch fetch all commit messages in one git call
        branch_commits = self.get_all_branch_commits()

        # Filter to worker worktrees only
        worker_worktrees = [
            wt for wt in worktrees if wt["path"] != main_path and not wt.get("detached")
        ]

        # Parallelize per-worker status fetching
        with ThreadPoolExecutor() as executor:
            workers = list(
                executor.map(
                    lambda wt: self.get_worker_details(wt, default_branch, branch_commits),
                    worker_worktrees,
                )
            )

        # Schedule UI update on the main thread
        self.call_from_thread(self._update_worker_table, workers)

    def _update_worker_table(self, workers: list[dict]) -> None:
        """Update the worker table UI (must be called from main thread)."""
        self.worker_list = workers

        # Update table
        table = self.query_one(WorkerTable)
        table.clear()

        for w in workers:
            path = Path(w["path"]).name
            branch = w.get("branch", "?")
            ahead = f"+{w.get('ahead', 0)}"
            commit = w.get("last_commit", "")[:40]
            activity = w.get("activity", "")
            status = w.get("status", "?")

            # Color activity based on git status prefix
            if activity.startswith("M"):
                activity = f"[yellow]{activity}[/]"
            elif activity.startswith("A") or activity.startswith("??"):
                activity = f"[green]{activity}[/]"
            elif activity.startswith("D"):
                activity = f"[red]{activity}[/]"
            elif activity == "idle":
                activity = "[dim]idle[/]"

            # Color status
            if status == "clean":
                status = "[green]clean[/]"
            elif status == "modified":
                status = "[yellow]modified[/]"
            elif status == "missing":
                status = "[red]missing[/]"

            table.add_row(path, branch, ahead, commit, activity, status)

        # Reset cursor to valid position after table rebuild
        if table.row_count > 0:
            table.move_cursor(row=min(table.cursor_row or 0, table.row_count - 1))
        else:
            table.move_cursor(row=0)

        # Update status bar
        status_bar = self.query_one(WorkerStatus)
        status_bar.update_stats(workers)

    def action_refresh(self) -> None:
        """Manual refresh."""
        self.refresh_workers()
        self.notify("Refreshed")

    def action_cleanup(self) -> None:
        """Clean up merged worktrees."""
        default_branch = get_default_branch()
        result = subprocess.run(
            ["git", "branch", "--merged", default_branch],
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
        worker = self._get_selected_worker()
        if worker:
            branch = worker.get("branch")
            if branch:
                # Would need to be async in real implementation
                self.notify(f"Would create PR for {branch}")
        else:
            self.notify("No worker selected", severity="warning")

    def _get_selected_worker(self) -> dict | None:
        """Get the currently selected worker from the table."""
        table = self.query_one(WorkerTable)
        if table.cursor_row is not None and 0 <= table.cursor_row < len(self.worker_list):
            return self.worker_list[table.cursor_row]
        return None

    def action_show_details(self) -> None:
        """Show detailed info for selected worker."""
        worker = self._get_selected_worker()
        if worker:
            self.push_screen(WorkerDetailScreen(worker, view="info"))
        else:
            self.notify("No worker selected", severity="warning")

    def action_show_logs(self) -> None:
        """Show commit logs for selected worker."""
        worker = self._get_selected_worker()
        if worker:
            self.push_screen(WorkerDetailScreen(worker, view="logs"))
        else:
            self.notify("No worker selected", severity="warning")

    def action_show_diff(self) -> None:
        """Show diff for selected worker."""
        worker = self._get_selected_worker()
        if worker:
            self.push_screen(WorkerDetailScreen(worker, view="diff"))
        else:
            self.notify("No worker selected", severity="warning")


def main():
    app = WorkerApp()
    app.run()


if __name__ == "__main__":
    main()
