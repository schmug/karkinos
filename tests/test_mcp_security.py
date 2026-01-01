import unittest
from unittest.mock import patch
from pathlib import Path
import sys
import os
import tempfile
import shutil

# Add src to python path so we can import the server module
sys.path.insert(0, os.path.abspath("karkinos-plugin/servers/karkinos-mcp"))

import server

class TestSecurity(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.worktree_path = Path(self.test_dir) / "worktree"
        self.worktree_path.mkdir()

        # Create a file inside worktree
        (self.worktree_path / "safe.txt").write_text("safe content")

        # Create a file outside worktree
        (Path(self.test_dir) / "secret.txt").write_text("secret content")

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    @patch('server.get_worktrees')
    def test_read_file_path_traversal(self, mock_get_worktrees):
        """Test that read_file prevents path traversal using real file system operations."""

        # Setup mock to return our temporary worktree
        mock_get_worktrees.return_value = [
            {"branch": "feature-branch", "path": str(self.worktree_path)}
        ]

        # 1. Test normal access (safe)
        result = server.read_file("feature-branch", "safe.txt")
        self.assertEqual(result.get("content"), "safe content")

        # 2. Test traversal (unsafe)
        # Try to access ../secret.txt
        result = server.read_file("feature-branch", "../secret.txt")

        # Should return an error
        self.assertIn("error", result)
        self.assertIn("Access denied", result["error"])

        # 3. Test sibling directory attack (if applicable)
        # Create a sibling directory "worktree-sibling"
        sibling_path = Path(self.test_dir) / "worktree-sibling"
        sibling_path.mkdir()
        (sibling_path / "other.txt").write_text("other content")

        result = server.read_file("feature-branch", "../worktree-sibling/other.txt")
        self.assertIn("error", result)
        self.assertIn("Access denied", result["error"])

if __name__ == '__main__':
    unittest.main()
