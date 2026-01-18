import unittest
import sys
import os
from pathlib import Path

# Add the server directory to path
server_path = Path("karkinos-plugin/servers/karkinos-mcp").resolve()
sys.path.insert(0, str(server_path))

from server import validate_branch_name

class TestBranchValidation(unittest.TestCase):
    def test_valid_branches(self):
        """Test valid branch names."""
        valid_names = [
            "main",
            "feature/new-feature",
            "fix_bug_123",
            "user/name/repo",
            "v1.0.0",
        ]
        for name in valid_names:
            try:
                validate_branch_name(name)
            except ValueError as e:
                self.fail(f"Valid branch '{name}' raised ValueError: {e}")

    def test_invalid_branches(self):
        """Test invalid branch names that should be rejected."""
        invalid_names = [
            "-starts-with-dash", # Already covered
            "contains space",
            "feature..range", # Double dot is special in git
            "@{upstream}", # Git ref syntax
            "refs/heads/master", # Should be short name? Maybe okay, but strictly we want simple names
            "name-with-wildcard*", # Wildcard
            "semi:colon",
            "question?mark",
            "bracket[",
            "caret^",
            "tilde~",
            "back\\slash",
            "end-with-dot.",
            "end-with-slash/",
            "double//slash",
        ]

        for name in invalid_names:
            with self.subTest(name=name):
                with self.assertRaises(ValueError, msg=f"Should reject '{name}'"):
                    validate_branch_name(name)

if __name__ == "__main__":
    unittest.main()
