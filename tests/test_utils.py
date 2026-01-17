import pytest
from karkinos.utils import validate_branch_name

def test_validate_branch_name():
    # Valid names
    validate_branch_name("main")
    validate_branch_name("feature/abc")
    validate_branch_name("fix-123")

    # Invalid names
    with pytest.raises(ValueError, match="cannot start with '-'"):
        validate_branch_name("-bad")

    with pytest.raises(ValueError, match="cannot start with '-'"):
        validate_branch_name("--bad")

    with pytest.raises(ValueError, match="cannot be empty"):
        validate_branch_name("")
