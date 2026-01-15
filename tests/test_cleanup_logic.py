import sys
import os
import unittest
from unittest.mock import MagicMock, patch

# Add src to python path so we can import karkinos
sys.path.insert(0, os.path.abspath("src"))

from karkinos.tui import WorkerApp, ConfirmationScreen

class TestCleanupConfirmation(unittest.TestCase):
    def test_cleanup_confirmation(self):
        app = WorkerApp()
        app.worker_list = [
            {"path": "/tmp/wt1", "branch": "feature/1"},
            {"path": "/tmp/wt2", "branch": "feature/2"},
        ]

        # Mock notify
        app.notify = MagicMock()
        # Mock push_screen
        app.push_screen = MagicMock()
        # Mock refresh_workers (called by _do_cleanup)
        app.refresh_workers = MagicMock()

        with patch("subprocess.run") as mock_run:
            # Mock get_default_branch
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "main"

            # 1. Test with no merged branches
            # Second call to subprocess.run in action_cleanup is git branch --merged
            def side_effect(*args, **kwargs):
                cmd = args[0]
                if "symbolic-ref" in cmd:
                    return MagicMock(returncode=0, stdout="refs/remotes/origin/main")
                if "branch" in cmd and "--merged" in cmd:
                    return MagicMock(returncode=0, stdout="") # No merged branches
                return MagicMock(returncode=0, stdout="")

            mock_run.side_effect = side_effect

            app.action_cleanup()
            app.notify.assert_called_with("No merged worktrees to clean up")
            app.push_screen.assert_not_called()

            # 2. Test with merged branches
            app.notify.reset_mock()

            def side_effect_merged(*args, **kwargs):
                cmd = args[0]
                if "symbolic-ref" in cmd:
                    return MagicMock(returncode=0, stdout="refs/remotes/origin/main")
                if "branch" in cmd and "--merged" in cmd:
                    return MagicMock(returncode=0, stdout="feature/1\n") # feature/1 is merged
                return MagicMock(returncode=0, stdout="")

            mock_run.side_effect = side_effect_merged

            app.action_cleanup()

            # Verify push_screen was called
            self.assertTrue(app.push_screen.called)
            args, kwargs = app.push_screen.call_args
            screen = args[0]
            callback = args[1]

            self.assertIsInstance(screen, ConfirmationScreen)
            self.assertIn("Delete 1 merged worktree(s)?", screen.message)

            # 3. Verify callback triggers _do_cleanup
            # We can't verify logic inside _do_cleanup easily without more mocks,
            # but we can verify it calls subprocess to remove worktree

            # Reset mocks
            mock_run.reset_mock()
            mock_run.side_effect = None
            # We want to check calls, so simple return values
            mock_run.return_value = MagicMock(returncode=0, stdout="")

            # Call the callback with True
            callback(True)

            # Check if git worktree remove /tmp/wt1 was called
            # Calls:
            # 1. git worktree remove /tmp/wt1
            # 2. git branch -d feature/1

            calls = mock_run.call_args_list
            # Check for worktree remove
            worktree_remove_called = any(
                "worktree" in c[0][0] and "remove" in c[0][0] and "/tmp/wt1" in c[0][0]
                for c in calls
            )
            self.assertTrue(worktree_remove_called, "Should attempt to remove worktree")

            # Check for branch delete
            branch_delete_called = any(
                "branch" in c[0][0] and "-d" in c[0][0] and "feature/1" in c[0][0]
                for c in calls
            )
            self.assertTrue(branch_delete_called, "Should attempt to delete branch")

            # Check that refresh_workers was called
            app.refresh_workers.assert_called()

            print("Verification passed!")

if __name__ == "__main__":
    unittest.main()
