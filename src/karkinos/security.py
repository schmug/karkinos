"""Security utilities for Karkinos."""


def validate_branch_name(branch: str) -> None:
    """
    Validate branch name to prevent argument injection.

    Ensures the branch name is safe to pass to git CLI commands.
    Specifically rejects names starting with '-' which could be interpreted as flags.

    Args:
        branch: The branch name to validate.

    Raises:
        ValueError: If the branch name is unsafe or invalid.
    """
    if not branch:
        raise ValueError("Branch name cannot be empty")

    if branch.startswith("-"):
        raise ValueError(f"Branch name cannot start with '-': {branch}")

    if ".." in branch:
        raise ValueError(f"Branch name cannot contain '..': {branch}")

    # check for other dangerous characters if needed, but leading dash is
    # the primary vector for argument injection in subprocess calls.
