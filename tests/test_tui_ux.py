from textual.app import App, ComposeResult

from karkinos.tui import EmptyState


class TestApp(App):
    def compose(self) -> ComposeResult:
        yield EmptyState()

async def test_empty_state_message():
    """Test that EmptyState message promotes the /worker command."""
    widget = EmptyState()
    rendered = widget.render()

    # Check for presence of the agent command
    assert "/worker" in rendered
    assert "Use the worker command" in rendered

    # Check that manual command is still there
    assert "git worktree add" in rendered

# Removed the tautological test_worker_detail_focus as requested by review.
