import unittest
from unittest.mock import MagicMock, patch

from karkinos.cli import cmd_cleanup, get_commits_ahead, get_last_commit
from karkinos.utils import validate_branch_name


class TestGitSecurity(unittest.TestCase):
    def test_validate_branch_name(self):
        """Test that validate_branch_name correctly identifies safe and unsafe branch names."""
        # Safe names
        validate_branch_name("main")
        validate_branch_name("feature/test")
        validate_branch_name("user/123")

        # Unsafe names
        with self.assertRaises(ValueError):
            validate_branch_name("-f")
        with self.assertRaises(ValueError):
            validate_branch_name("-option")
        with self.assertRaises(ValueError):
            validate_branch_name("")

    @patch("subprocess.run")
    @patch("karkinos.cli.get_default_branch")
    def test_get_commits_ahead_security(self, mock_default, mock_run):
        """Test that get_commits_ahead validates branch names."""
        mock_default.return_value = "main"

        # Safe call
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "5"
        get_commits_ahead("feature")

        # Unsafe call
        with self.assertRaises(ValueError):
            get_commits_ahead("-f")

    @patch("subprocess.run")
    def test_get_last_commit_security(self, mock_run):
        """Test that get_last_commit uses -- separator and validates."""
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "commit msg"

        # Safe call
        get_last_commit("feature")
        args = mock_run.call_args[0][0]
        self.assertIn("--", args)

        # Unsafe call
        with self.assertRaises(ValueError):
            get_last_commit("-f")

    @patch("karkinos.cli.get_worktrees")
    @patch("karkinos.cli.get_default_branch")
    @patch("subprocess.run")
    def test_cmd_cleanup_security(self, mock_run, mock_default, mock_worktrees):
        """Test that cleanup command handles unsafe branch names correctly."""
        mock_default.return_value = "main"

        # Mock worktrees with one safe and one unsafe branch
        mock_worktrees.return_value = [
            {"path": "/path/to/main", "branch": "main"},
            {"path": "/path/to/safe", "branch": "safe-feature"},
            {"path": "/path/to/unsafe", "branch": "-unsafe"},
        ]

        # Mock git branch --merged to return all branches as merged
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "safe-feature\n-unsafe\nmain"

        # Run cleanup
        args = MagicMock()
        args.dry_run = False
        cmd_cleanup(args)

        # Verify calls
        # We expect safe-feature to be removed
        # We expect -unsafe to be skipped or handled safely if dry_run was True (but here False)
        # Actually in our implementation we try/except validate_branch_name and continue

        # Check that we called worktree remove for safe-feature
        safe_remove_call_found = False
        for call in mock_run.call_args_list:
            args_list = call[0][0]
            if args_list[:3] == ["git", "worktree", "remove"] and args_list[3] == "/path/to/safe":
                safe_remove_call_found = True

        self.assertTrue(safe_remove_call_found, "Should attempt to remove safe worktree")

        # Check that we did NOT call worktree remove for -unsafe
        unsafe_remove_call_found = False
        for call in mock_run.call_args_list:
            args_list = call[0][0]
            if args_list[:3] == ["git", "worktree", "remove"] and args_list[3] == "/path/to/unsafe":
                unsafe_remove_call_found = True

        self.assertFalse(unsafe_remove_call_found, "Should NOT attempt to remove unsafe worktree")


if __name__ == "__main__":
    unittest.main()
