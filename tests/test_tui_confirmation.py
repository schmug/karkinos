import unittest
from unittest.mock import MagicMock, patch
from textual.app import App
from karkinos.tui import WorkerApp, ConfirmationScreen

class TestConfirmation(unittest.IsolatedAsyncioTestCase):
    async def test_confirmation_screen_y(self):
        """Test that pressing 'y' confirms the action."""
        screen = ConfirmationScreen("Are you sure?")
        app = App()

        confirmed = False
        def on_confirm(result):
            nonlocal confirmed
            confirmed = result

        async with app.run_test() as pilot:
            await app.push_screen(screen, on_confirm)
            await pilot.press("y")
            self.assertTrue(confirmed)

    async def test_confirmation_screen_n(self):
        """Test that pressing 'n' cancels the action."""
        screen = ConfirmationScreen("Are you sure?")
        app = App()

        confirmed = None
        def on_confirm(result):
            nonlocal confirmed
            confirmed = result

        async with app.run_test() as pilot:
            await app.push_screen(screen, on_confirm)
            await pilot.press("n")
            self.assertFalse(confirmed)

    @patch("karkinos.tui.WorkerApp.refresh_workers")
    @patch("karkinos.tui.subprocess.run")
    async def test_cleanup_trigger(self, mock_run, mock_refresh):
        """Test that cleanup action triggers the confirmation screen."""
        app = WorkerApp(show_crabs=False)

        # Mock git calls
        def side_effect(cmd, **kwargs):
            mock_res = MagicMock()
            mock_res.returncode = 0
            if "symbolic-ref" in cmd:
                mock_res.stdout = "refs/remotes/origin/main"
            elif "branch" in cmd and "--merged" in cmd:
                mock_res.stdout = "merged-branch\n"
            else:
                mock_res.stdout = ""
            return mock_res

        mock_run.side_effect = side_effect

        async with app.run_test() as pilot:
            # Manually set worker list after app start (since we mocked refresh)
            app.worker_list = [
                {"path": "/tmp/wt1", "branch": "merged-branch", "status": "clean"}
            ]

            # Trigger cleanup
            await pilot.press("c")

            # Check that ConfirmationScreen is pushed
            await pilot.pause()

            self.assertIsInstance(app.screen, ConfirmationScreen)
            self.assertIn("Delete 1 merged worktree", app.screen.message)

            # Now verify confirmation proceeds
            await pilot.press("y")
            await pilot.pause()

            # Verify cleanup commands were called
            # We expect: git worktree remove /tmp/wt1 AND git branch -d merged-branch

            calls = [c[0][0] for c in mock_run.call_args_list]
            # Flatten arguments
            flat_calls = [" ".join(args) for args in calls]

            # Filter for our expected calls
            wt_calls = [c for c in flat_calls if "worktree remove /tmp/wt1" in c]
            br_calls = [c for c in flat_calls if "branch -d merged-branch" in c]

            self.assertTrue(wt_calls, f"Worktree remove not called. Calls: {flat_calls}")
            self.assertTrue(br_calls, f"Branch delete not called. Calls: {flat_calls}")
