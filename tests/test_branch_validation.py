import unittest
import sys
import os

# Add src to python path so we can import the server module
sys.path.insert(0, os.path.abspath("karkinos-plugin/servers/karkinos-mcp"))

import server

class TestBranchValidation(unittest.TestCase):
    def test_valid_branches(self):
        valid_branches = [
            "main",
            "feature/new-stuff",
            "fix/bug-123",
            "v1.0.0",
            "user_name/branch",
            "feature-with-dashes",
        ]
        for branch in valid_branches:
            try:
                server.validate_branch_name(branch)
            except ValueError as e:
                self.fail(f"validate_branch_name raised ValueError unexpectedly for '{branch}': {e}")

    def test_invalid_branches(self):
        invalid_branches = [
            ("", "Branch name cannot be empty"),
            ("-start-with-dash", "cannot start with '-'"),
            ("branch with spaces", "contains invalid characters"),
            ("branch..name", "cannot contain '..'"),
            ("../traversal", "cannot contain '..'"),
            ("@{u}", "contains invalid characters"),
            ("branch.lock", "cannot end with '.lock'"),
            ("branch/", "cannot end with '/' or '.'"),
            ("branch.", "cannot end with '/' or '.'"),
            ("//double-slash", "cannot contain '//'"),
            ("; echo hacked", "contains invalid characters"),
            ("& echo hacked", "contains invalid characters"),
        ]

        for branch, error_msg_part in invalid_branches:
            with self.assertRaises(ValueError, msg=f"Should fail for '{branch}'"):
                server.validate_branch_name(branch)

            try:
                server.validate_branch_name(branch)
            except ValueError as e:
                # Some checks might be preempted by regex check (e.g. @{u} is invalid char before @{ check)
                # So we only check strict message if we are sure it's the specific check
                if "invalid characters" not in str(e):
                    self.assertIn(error_msg_part, str(e), f"Error message for '{branch}' should contain '{error_msg_part}'")

if __name__ == '__main__':
    unittest.main()
