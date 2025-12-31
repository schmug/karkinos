# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

```bash
# Install in development mode
uv pip install -e .

# Lint
ruff check src/

# Format
ruff format src/

# Run the CLI
karkinos list          # List active workers
karkinos watch         # Launch TUI monitor
karkinos init          # Add skills/commands to current project
karkinos cleanup       # Remove merged worktrees (--dry-run to preview)
```

## Architecture

Karkinos enables parallel Claude Code development using git worktrees. It spawns worker Claudes in isolated branches while an orchestrator monitors progress.

### Source Structure

- `src/karkinos/cli.py` - CLI entry point (`karkinos` command). Handles `list`, `watch`, `init`, `cleanup` subcommands. Uses subprocess for all git operations.
- `src/karkinos/tui.py` - Textual-based TUI for monitoring workers. Auto-refreshes every 5 seconds. Keybindings: `r` refresh, `c` cleanup, `p` create PR, `q` quit.

### Claude Integration

- `claude/commands/*.md` - Slash command definitions (`/worker`, `/workers`, `/issue-worker`, `/pr-worker`, `/worker-cleanup`)
- `claude/skills/*/SKILL.md` - Skill implementations that get copied to projects via `karkinos init`

### Key Patterns

- Worktrees created at `../<project>-<branch-slug>` (sibling to main repo)
- Workers run with `claude --print --dangerously-skip-permissions` for autonomous operation
- Commit counts measured relative to `main` branch
- Status tracking: "clean" (no uncommitted changes) vs "modified"
