import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# Ensure src is in path
sys.path.insert(0, os.path.abspath("src"))

from karkinos import cli, tui


class TestOptimizations(unittest.TestCase):
    def test_tui_get_default_branch_memoization(self):
        if hasattr(tui.get_default_branch, "cache_clear"):
            tui.get_default_branch.cache_clear()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="refs/remotes/origin/main\n")

            r1 = tui.get_default_branch()
            r2 = tui.get_default_branch()

            self.assertEqual(r1, "main")
            self.assertEqual(r2, "main")
            self.assertEqual(
                mock_run.call_count,
                1,
                f"tui.get_default_branch called {mock_run.call_count} times, expected 1",
            )

    def test_cli_get_default_branch_memoization(self):
        if hasattr(cli.get_default_branch, "cache_clear"):
            cli.get_default_branch.cache_clear()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="refs/remotes/origin/dev\n")

            r1 = cli.get_default_branch()
            r2 = cli.get_default_branch()

            self.assertEqual(r1, "dev")
            self.assertEqual(r2, "dev")
            self.assertEqual(
                mock_run.call_count,
                1,
                f"cli.get_default_branch called {mock_run.call_count} times, expected 1",
            )

if __name__ == "__main__":
    unittest.main()
