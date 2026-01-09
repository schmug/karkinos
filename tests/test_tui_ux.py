import pytest
from karkinos.tui import format_sync_status

def test_format_sync_status():
    """Test the sync status formatter logic."""
    # Synced state
    assert format_sync_status(0, 0) == "[dim]sync[/]"

    # Ahead only
    assert format_sync_status(5, 0) == "[green]+5[/]"

    # Behind only
    assert format_sync_status(0, 3) == "[red]-3[/]"

    # Diverged state
    assert format_sync_status(2, 4) == "[green]+2[/] [red]-4[/]"
