import contextlib
import io
import unittest
from unittest.mock import MagicMock, patch

from karkinos import cli


class TestArgInjection(unittest.TestCase):
    @patch("karkinos.cli.subprocess.run")
    def test_cli_get_commits_ahead_injection(self, mock_run):
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "1"

        # Malicious branch name
        malicious_branch = "-option"

        # This should now return 0 because of validation failure
        result = cli.get_commits_ahead(malicious_branch, default_branch="main")

        self.assertEqual(result, 0)

        # We expect ZERO calls to git rev-list because validation fails.
        for call_args in mock_run.call_args_list:
            cmd = call_args[0][0]
            if "rev-list" in cmd:
                self.fail(f"git rev-list called with malicious input: {cmd}")

    @patch("karkinos.cli.subprocess.run")
    def test_cli_cleanup_injection(self, mock_run):
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = ""

        # Mock get_worktrees to return a malicious branch
        with patch("karkinos.cli.get_worktrees") as mock_get_worktrees:
            mock_get_worktrees.return_value = [{"path": "/tmp/wt", "branch": "-D"}]

            # Setup mock to return -D as merged
            def side_effect(cmd, **kwargs):
                if "branch" in cmd and "--merged" in cmd:
                    return MagicMock(returncode=0, stdout="-D\n")
                return MagicMock(returncode=0, stdout="")

            mock_run.side_effect = side_effect

            # Capture stdout to check for skip message
            f = io.StringIO()
            with contextlib.redirect_stdout(f):
                args = MagicMock()
                args.dry_run = False
                cli.cmd_cleanup(args)

            output = f.getvalue()
            self.assertIn("Skipping unsafe branch name: -D", output)

            # verify git branch -d was NOT called
            for call_args in mock_run.call_args_list:
                cmd = call_args[0][0]
                if "branch" in cmd and "-d" in cmd:
                    self.fail(f"git branch -d called for unsafe branch: {cmd}")

    @patch("karkinos.cli.subprocess.run")
    def test_cli_cleanup_valid(self, mock_run):
        """Verify valid branch is handled correctly with -- separator."""
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = ""

        # Mock get_worktrees to return a VALID branch
        with patch("karkinos.cli.get_worktrees") as mock_get_worktrees:
            mock_get_worktrees.return_value = [{"path": "/tmp/wt", "branch": "feature/safe"}]

            def side_effect(cmd, **kwargs):
                if "branch" in cmd and "--merged" in cmd:
                    return MagicMock(returncode=0, stdout="feature/safe\n")
                return MagicMock(returncode=0, stdout="")

            mock_run.side_effect = side_effect

            args = MagicMock()
            args.dry_run = False

            # Capture stdout
            f = io.StringIO()
            with contextlib.redirect_stdout(f):
                cli.cmd_cleanup(args)

            # verify git branch -d was called WITH -- separator
            # We look for ['git', 'branch', '-d', '--', 'feature/safe']
            found = False
            for call_args in mock_run.call_args_list:
                cmd = call_args[0][0]
                if cmd[:4] == ["git", "branch", "-d", "--"] and cmd[4] == "feature/safe":
                    found = True
                    break

            self.assertTrue(found, "Should have called 'git branch -d -- feature/safe'")


if __name__ == "__main__":
    unittest.main()
