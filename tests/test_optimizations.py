import unittest
from unittest.mock import patch
import sys
import os

# Ensure we can import the modules
sys.path.insert(0, os.path.abspath("src"))
sys.path.insert(0, os.path.abspath("karkinos-plugin/servers/karkinos-mcp"))

from karkinos import tui
from karkinos import cli
import server

class TestOptimizations(unittest.TestCase):

    @patch('subprocess.run')
    def test_tui_get_default_branch_cached(self, mock_run):
        """Test that tui.get_default_branch is cached."""
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "refs/remotes/origin/main"

        # Clear cache first
        tui.get_default_branch.cache_clear()

        # Call multiple times
        val1 = tui.get_default_branch()
        val2 = tui.get_default_branch()
        val3 = tui.get_default_branch()

        self.assertEqual(val1, "main")
        self.assertEqual(val2, "main")
        self.assertEqual(val3, "main")

        # Should be called only once
        mock_run.assert_called_once()

        # Verify cache info
        info = tui.get_default_branch.cache_info()
        self.assertGreater(info.hits, 0)

    @patch('subprocess.run')
    def test_cli_get_default_branch_cached(self, mock_run):
        """Test that cli.get_default_branch is cached."""
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "refs/remotes/origin/master"

        # Clear cache first
        cli.get_default_branch.cache_clear()

        # Call multiple times
        val1 = cli.get_default_branch()
        val2 = cli.get_default_branch()
        val3 = cli.get_default_branch()

        self.assertEqual(val1, "master")
        self.assertEqual(val2, "master")
        self.assertEqual(val3, "master")

        # Should be called only once
        mock_run.assert_called_once()

    @patch('subprocess.run')
    def test_server_get_default_branch_cached(self, mock_run):
        """Test that server.get_default_branch is cached."""
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "refs/remotes/origin/develop"

        # Clear cache first
        server.get_default_branch.cache_clear()

        # Call multiple times
        val1 = server.get_default_branch()
        val2 = server.get_default_branch()
        val3 = server.get_default_branch()

        self.assertEqual(val1, "develop")
        self.assertEqual(val2, "develop")
        self.assertEqual(val3, "develop")

        # Should be called only once
        mock_run.assert_called_once()

if __name__ == '__main__':
    unittest.main()
