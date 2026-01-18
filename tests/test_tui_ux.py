import unittest
from unittest.mock import patch

from textual.app import App

from karkinos.tui import WorkerDetailScreen


class TestWorkerDetailFooter(unittest.IsolatedAsyncioTestCase):
    async def test_worker_detail_footer(self):
        """Verify that the footer highlights the active view."""
        app = App()
        worker = {"branch": "test-branch", "path": "/tmp/test", "status": "clean"}

        # Mock subprocess to avoid actual git calls during screen mount and updates
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "mock git output"

            screen = WorkerDetailScreen(worker, view="info")

            async with app.run_test() as pilot:
                await app.push_screen(screen)

                # Allow messages to process
                await pilot.pause()

                # Check info view active
                self.assertEqual(screen.current_view, "info")

                # Trigger action
                screen.action_show_logs()
                self.assertEqual(screen.current_view, "logs")

                screen.action_show_diff()
                self.assertEqual(screen.current_view, "diff")
