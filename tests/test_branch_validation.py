import unittest
import sys
import os
import re

# Add src to python path so we can import the server module
sys.path.insert(0, os.path.abspath("karkinos-plugin/servers/karkinos-mcp"))

import server

class TestBranchValidation(unittest.TestCase):

    def test_valid_branch_names(self):
        """Test that valid branch names are accepted."""
        valid_names = [
            "main",
            "master",
            "feature/login-page",
            "bugfix/issue-123",
            "v1.0.0",
            "user_name/feature",
            "deploy-2023",
        ]
        for name in valid_names:
            try:
                server.validate_branch_name(name)
            except ValueError as e:
                self.fail(f"Valid branch name '{name}' raised ValueError: {e}")

    def test_invalid_branch_names(self):
        """Test that invalid branch names are rejected."""
        invalid_names = [
            "-flag",          # Argument injection (already caught)
            "--option",       # Argument injection (already caught)
            "foo bar",        # Space not allowed
            "foo;rm -rf /",   # Shell metacharacter
            "foo|pipe",       # Pipe
            "foo&bar",        # Ampersand
            "$(command)",     # Command substitution
            "`command`",      # Backticks
            "refs/heads/main",# Should not include refs/ prefix
            "foo..bar",       # Double dot (range)
            "foo//bar",       # Double slash
            "foo/.",          # Ends with dot
            "foo/",           # Ends with slash
            "/foo",           # Starts with slash (questionable, but usually bad practice for branch name inputs)
            "@{upstream}",    # Git revision syntax
        ]

        for name in invalid_names:
            with self.subTest(name=name):
                with self.assertRaises(ValueError, msg=f"Invalid branch name '{name}' should have raised ValueError"):
                    server.validate_branch_name(name)

if __name__ == '__main__':
    unittest.main()
