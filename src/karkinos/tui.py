"""Karkinos TUI - Monitor parallel Claude workers."""

import random
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


class EmptyState(Static):
    """Widget to show when no workers are found."""

    def render(self) -> str:
        return (
            "\n"
            "[bold]No active worktrees found[/]\n"
            "\n"
            "Create a new git worktree to get started!\n"
            "[dim]git worktree add ../<name> <branch>[/]"
        )


class CrabSprite:
    """Individual crab sprite with position, direction, and expression."""

    EXPRESSIONS = ["i_i", "-_-", ". .", "°°", "^^"]

    def __init__(self, x: int, direction: int = 1):
        self.x = x
        self.direction = direction
        self.expression = random.choice(self.EXPRESSIONS)

    def render(self) -> str:
        """Render the crab as ASCII art."""
        if self.direction > 0:
            # Moving right: claws on left
            return f"(\\/)({self.expression})(\\/)"
        else:
            # Moving left: claws on right (mirrored look)
            return f"(\\/)({self.expression})(\\/)"

    def move(self, min_x: int, max_x: int) -> None:
        """Move the crab and bounce off edges."""
        self.x += self.direction
        if self.x <= min_x:
            self.x = min_x
            self.direction = 1
        elif self.x >= max_x:
            self.x = max_x
            self.direction = -1
        # 10% chance to change expression on each move
        if random.random() < 0.1:
            self.expression = random.choice(self.EXPRESSIONS)

    @property
    def width(self) -> int:
        """Width of the rendered crab."""
        return len(self.render())


class CrabHeader(Static):
    """ASCII crab header with animated crabs walking across."""

    frame: reactive[int] = reactive(0)

    def __init__(self, animate: bool = True, speed: float = 0.4, **kwargs):
        super().__init__(**kwargs)
        self.animate = animate
        self.speed = speed
        self.left_crab = CrabSprite(x=0, direction=1)
        self.right_crab = CrabSprite(x=10, direction=-1)

    def on_mount(self) -> None:
        """Start the animation timer if enabled."""
        if self.animate:
            self.set_interval(self.speed, self._next_frame)

    def _next_frame(self) -> None:
        """Advance animation frame."""
        # Move crabs with wider shuffle range
        self.left_crab.move(0, 15)
        self.right_crab.move(0, 15)
        self.frame = (self.frame + 1) % 1000

    def watch_frame(self) -> None:
        """React to frame changes by refreshing."""
        self.refresh()

    def render(self) -> str:
        """Render crabs with center text fixed, crabs move in side zones."""
        center_rich = "[cyan]KARKINOS[/cyan] [bold cyan]Worker Monitor[/bold cyan]"

        if not self.animate:
            # Static header without crabs
            return f"  🦀  {center_rich}  🦀  "

        try:
            width = self.size.width or 80
        except Exception:
            width = 80

        center = "KARKINOS Worker Monitor"

        # Calculate zones: |--left zone--|--center--|--right zone--|
        center_start = (width - len(center)) // 2
        zone_width = center_start - 2  # Leave 2 char padding

        # Build left zone with crab
        left_crab_str = self.left_crab.render()
        left_pos = min(self.left_crab.x, zone_width - len(left_crab_str))
        left_zone = " " * left_pos + f"[bold orange1]{left_crab_str}[/]"
        left_zone += " " * (zone_width - left_pos - len(left_crab_str))

        # Build right zone with crab
        right_crab_str = self.right_crab.render()
        right_pos = min(self.right_crab.x, zone_width - len(right_crab_str))
        right_zone = " " * (zone_width - right_pos - len(right_crab_str))
        right_zone += f"[bold orange1]{right_crab_str}[/]"
        right_zone += " " * right_pos

        return f"{left_zone}  {center_rich}  {right_zone}"


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

    #empty-state {
        height: 100%;
        align: center middle;
        text-align: center;
        color: $text-muted;
        display: none;
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
        ("u", "update_branches", "Update branches"),
        ("c", "cleanup", "Cleanup merged"),
        ("p", "create_pr", "Create PR"),
        ("enter", "show_details", "Details"),
        ("l", "show_logs", "Logs"),
        ("d", "show_diff", "Diff"),
    ]

    worker_list: reactive[list[dict]] = reactive([])

    def __init__(self, show_crabs: bool = True, animation_speed: float = 0.4):
        super().__init__()
        self.show_crabs = show_crabs
        self.animation_speed = animation_speed
        self.refresh_timer: Timer | None = None
        # Cache: branch -> (ci_status, review_status, timestamp)
        self._pr_status_cache: dict[str, tuple[str, str, float]] = {}
        self._cache_ttl = 30.0  # seconds

    def compose(self) -> ComposeResult:
        yield CrabHeader(animate=self.show_crabs, speed=self.animation_speed)
        yield Container(
            WorkerStatus(id="status-bar"),
            WorkerTable(id="worker-table"),
            EmptyState(id="empty-state"),
            id="main-container",
        )
        yield Footer()

    def on_mount(self) -> None:
        """Set up the table and start refresh timer."""
        table = self.query_one(WorkerTable)
        table.add_columns("Worktree", "Branch", "Ahead", "CI", "Review", "Changes", "Status")

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

    def get_branch_details(self, default_branch: str) -> dict[str, dict]:
        """Batch fetch branch details (subject, ahead count) in one git call."""
        # Use fallback if default_branch is empty
        target = default_branch or "main"
        result = subprocess.run(
            [
                "git",
                "for-each-ref",
                f"--format=%(refname:short)|%(subject)|%(ahead-behind:{target})",
                "refs/heads/",
            ],
            capture_output=True,
            text=True,
        )
        details = {}
        if result.returncode == 0:
            for line in result.stdout.strip().split("\n"):
                # Split from right to preserve pipes in commit subject
                # Format: refname|subject|ahead behind
                parts = line.rsplit("|", 2)
                if len(parts) == 3:
                    branch = parts[0]
                    subject = parts[1]
                    ahead_behind = parts[2]
                    try:
                        ahead, _ = map(int, ahead_behind.split())
                    except ValueError:
                        ahead = 0

                    details[branch] = {"subject": subject, "ahead": ahead}
        return details

    def get_pr_status(self, branch: str) -> tuple[str, str]:
        """Get CI and review status for a branch's PR.

        Returns:
            Tuple of (ci_status, review_status)
            ci_status: "pass", "fail", "...", "-" (no PR)
            review_status: "ok", "chg", "req", "-" (no PR)
        """
        import json
        import time

        # Check cache
        if branch in self._pr_status_cache:
            ci, review, timestamp = self._pr_status_cache[branch]
            if time.time() - timestamp < self._cache_ttl:
                return (ci, review)

        # Fetch PR status
        result = subprocess.run(
            ["gh", "pr", "view", branch, "--json", "statusCheckRollup,reviewDecision,state"],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            return ("-", "-")  # No PR exists

        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError:
            return ("-", "-")

        # CI Status from statusCheckRollup
        checks = data.get("statusCheckRollup", []) or []
        if not checks:
            ci_status = "-"
        else:
            conclusions = [c.get("conclusion") for c in checks if c.get("conclusion")]
            states = [c.get("status") for c in checks]

            if any(c == "FAILURE" for c in conclusions):
                ci_status = "fail"
            elif all(c == "SUCCESS" for c in conclusions if c):
                ci_status = "pass"
            elif any(s in ("IN_PROGRESS", "PENDING", "QUEUED") for s in states):
                ci_status = "..."
            else:
                ci_status = "?"

        # Review status
        review = data.get("reviewDecision", "")
        if review == "APPROVED":
            review_status = "ok"
        elif review == "CHANGES_REQUESTED":
            review_status = "chg"
        elif review == "REVIEW_REQUIRED":
            review_status = "req"
        else:
            review_status = "-"

        # Update cache
        self._pr_status_cache[branch] = (ci_status, review_status, time.time())
        return (ci_status, review_status)

    def get_worker_details(
        self, wt: dict, default_branch: str, branch_details: dict[str, dict]
    ) -> dict:
        """Enrich worktree with additional details."""
        branch = wt.get("branch", "")
        details = branch_details.get(branch, {})

        # Commits ahead of default branch (from pre-fetched batch)
        wt["ahead"] = details.get("ahead", 0)

        # Last commit (from pre-fetched batch)
        wt["last_commit"] = details.get("subject", "")[:50]

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

        # PR status (CI and review)
        if branch:
            ci_status, review_status = self.get_pr_status(branch)
            wt["ci_status"] = ci_status
            wt["review_status"] = review_status
        else:
            wt["ci_status"] = "-"
            wt["review_status"] = "-"

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

        # Batch fetch all commit messages and ahead counts in one git call
        branch_details = self.get_branch_details(default_branch)

        # Filter to worker worktrees only
        worker_worktrees = [
            wt for wt in worktrees if wt["path"] != main_path and not wt.get("detached")
        ]

        # Parallelize per-worker status fetching
        with ThreadPoolExecutor() as executor:
            workers = list(
                executor.map(
                    lambda wt: self.get_worker_details(wt, default_branch, branch_details),
                    worker_worktrees,
                )
            )

        # Schedule UI update on the main thread
        self.call_from_thread(self._update_worker_table, workers)

    def _update_worker_table(self, workers: list[dict]) -> None:
        """Update the worker table UI (must be called from main thread)."""
        self.worker_list = workers

        # Update status bar
        status_bar = self.query_one(WorkerStatus)
        status_bar.update_stats(workers)

        # Update table
        table = self.query_one(WorkerTable)
        empty_state = self.query_one(EmptyState)
        table.clear()

        if not workers:
            table.display = False
            empty_state.display = True
            return

        table.display = True
        empty_state.display = False

        for w in workers:
            path = Path(w["path"]).name
            branch = w.get("branch", "?")
            ahead = f"+{w.get('ahead', 0)}"
            ci = w.get("ci_status", "-")
            review = w.get("review_status", "-")
            activity = w.get("activity", "")
            status = w.get("status", "?")

            # Color CI status
            if ci == "pass":
                ci = "[green]pass[/]"
            elif ci == "fail":
                ci = "[red]fail[/]"
            elif ci == "...":
                ci = "[yellow]...[/]"

            # Color review status
            if review == "ok":
                review = "[green]ok[/]"
            elif review == "chg":
                review = "[red]chg[/]"
            elif review == "req":
                review = "[yellow]req[/]"

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

            table.add_row(path, branch, ahead, ci, review, activity, status)

        # Reset cursor to valid position after table rebuild
        if table.row_count > 0:
            table.move_cursor(row=min(table.cursor_row or 0, table.row_count - 1))
        else:
            table.move_cursor(row=0)

    def action_refresh(self) -> None:
        """Manual refresh."""
        self._pr_status_cache.clear()  # Clear cache on manual refresh
        self.refresh_workers()
        self.notify("Refreshed")

    def action_update_branches(self) -> None:
        """Update all worker branches by rebasing onto main."""
        self.notify("Updating branches...")
        self._update_branches_async()

    @work(thread=True)
    def _update_branches_async(self) -> None:
        """Rebase all workers onto main in background thread."""
        # Fetch latest
        subprocess.run(["git", "fetch", "origin"], capture_output=True)

        default_branch = get_default_branch()
        updated = 0
        conflicts = 0
        skipped = 0

        for w in self.worker_list:
            path = w.get("path")
            branch = w.get("branch")
            status = w.get("status")

            if not path or not branch:
                continue

            # Skip workers with uncommitted changes
            if status == "modified":
                skipped += 1
                continue

            # Rebase onto main
            result = subprocess.run(
                ["git", "-C", path, "rebase", f"origin/{default_branch}"],
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                updated += 1
            else:
                # Abort failed rebase
                subprocess.run(
                    ["git", "-C", path, "rebase", "--abort"],
                    capture_output=True,
                )
                conflicts += 1

        # Build result message
        parts = []
        if updated:
            parts.append(f"{updated} updated")
        if conflicts:
            parts.append(f"{conflicts} conflicts")
        if skipped:
            parts.append(f"{skipped} skipped")
        msg = ", ".join(parts) if parts else "No branches to update"

        self.call_from_thread(self.notify, msg)
        self.call_from_thread(self.refresh_workers)

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
        if not worker:
            self.notify("No worker selected", severity="warning")
            return
        branch = worker.get("branch")
        if not branch:
            self.notify("No branch for worker", severity="warning")
            return
        self.notify(f"Creating PR for {branch}...")
        self._create_pr_async(branch)

    @work(thread=True)
    def _create_pr_async(self, branch: str) -> None:
        """Create PR in background thread."""
        import json

        # Check if PR already exists
        check_result = subprocess.run(
            ["gh", "pr", "view", branch, "--json", "url"],
            capture_output=True,
            text=True,
        )
        if check_result.returncode == 0:
            try:
                pr_data = json.loads(check_result.stdout)
                url = pr_data.get("url", "unknown")
                self.call_from_thread(self.notify, f"PR exists: {url}")
            except json.JSONDecodeError:
                self.call_from_thread(self.notify, "PR already exists")
            return

        # Push branch
        push_result = subprocess.run(
            ["git", "push", "-u", "origin", branch],
            capture_output=True,
            text=True,
        )
        if push_result.returncode != 0:
            self.call_from_thread(
                self.notify, f"Push failed: {push_result.stderr[:50]}", severity="error"
            )
            return

        # Get last commit message for PR title
        commit_result = subprocess.run(
            ["git", "log", branch, "--oneline", "-1", "--format=%s"],
            capture_output=True,
            text=True,
        )
        title = commit_result.stdout.strip() if commit_result.returncode == 0 else branch

        # Create PR
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
                "Created by Karkinos TUI\n\n---\nCrab Worker (Karkinos)",
            ],
            capture_output=True,
            text=True,
        )
        if pr_result.returncode != 0:
            self.call_from_thread(
                self.notify, f"PR creation failed: {pr_result.stderr[:50]}", severity="error"
            )
            return

        pr_url = pr_result.stdout.strip()

        # Enable auto-merge
        pr_number = pr_url.rstrip("/").split("/")[-1]
        merge_result = subprocess.run(
            ["gh", "pr", "merge", pr_number, "--auto", "--squash"],
            capture_output=True,
            text=True,
        )
        auto_merge_msg = " (auto-merge enabled)" if merge_result.returncode == 0 else ""

        self.call_from_thread(self.notify, f"PR created{auto_merge_msg}: {pr_url}")
        self.call_from_thread(self.refresh_workers)

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
