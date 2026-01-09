"""Utility functions for Karkinos."""


def validate_branch_name(branch: str) -> None:
    """Validate branch name to prevent argument injection."""
    if not branch:
        raise ValueError("Branch name cannot be empty")
    if branch.startswith("-"):
        raise ValueError(f"Invalid branch name '{branch}': cannot start with '-'")
