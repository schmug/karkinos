import unittest
from unittest.mock import patch, MagicMock
from karkinos import cli

class TestCliSecurity(unittest.TestCase):
    @patch('subprocess.run')
    def test_get_last_commit_injection(self, mock_run):
        # Simulate a branch named "-f"
        branch = "-f"

        # Mock successful return
        mock_run.return_value = MagicMock(returncode=0, stdout="hash msg")

        # This should effectively do nothing or return "" because of validation
        # Since I added validation, it should catch ValueError internally and return ""
        # OR raise ValueError if I didn't wrap it.

        # In cli.py:
        # try:
        #    validate_branch_name(branch)
        # except ValueError:
        #    return ""

        result = cli.get_last_commit(branch)

        # It should return empty string because branch is invalid
        self.assertEqual(result, "")

        # And subprocess should NOT be called
        mock_run.assert_not_called()

if __name__ == '__main__':
    unittest.main()
