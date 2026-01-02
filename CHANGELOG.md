# Changelog

All notable changes to Karkinos will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.1] - 2024-12-XX

### Added
- Auto-merge support for PRs in TUI (#47)
- TUI PR creation directly from worker table (#47)
- CI/review status columns in TUI (#47)
- IDE terminal integration for `watch --spawn` command

### Changed
- Renamed "Activity" column to "Changes" in TUI for clarity

### Fixed
- Documentation improvements for worker permissions security callout

## [0.2.0] - 2024-12-XX

### Added
- `karkinos watch --spawn` command for IDE terminal integration
- Plugin marketplace for easy distribution
- New skills bundled with installation
- MCP server tools:
  - `karkinos_read_file` - Read files from worker worktrees
  - `karkinos_get_diff` - Get diffs from worker worktrees
  - `karkinos_update_branches` - Update worker branches
- Activity column showing worker thinking snippets (#35)
- Animated crabs walking in TUI title bar (#43)
- TUI settings for crab animation control
- `--no-crabs` and `--speed` flags for animation customization

### Changed
- Complete feature documentation in README and AGENTS.md (#45)

### Fixed
- MCP server protocol and plugin manifest corrections
- Optimized TUI refresh with batching and parallelization (#37)

## [0.1.0] - 2024-11-XX

### Added
- Initial release of Karkinos
- Core parallel Claude worker functionality using git worktrees
- TUI monitor with `karkinos watch`
- ASCII crab mascot in TUI (#20)
- Worker inspection in TUI (#19)
- Workers can create their own PRs (#18)
- Slash commands:
  - `/worker` - Spawn worker in new worktree
  - `/issue-worker` - Work on GitHub issues
  - `/pr-worker` - Address PR feedback
  - `/workers` - List active workers
  - `/worker-cleanup` - Remove finished worktrees
- CLI commands:
  - `karkinos init` - Initialize project with skills/commands
  - `karkinos list` - List active workers
  - `karkinos watch` - Launch TUI monitor
  - `karkinos cleanup` - Remove merged worktrees
- TUI keybindings: `r` (refresh), `c` (cleanup), `p` (create PR), `Enter` (details), `l` (logs), `d` (diff), `q` (quit)
- Bundled commands and skills for distribution
- Claude Code plugin with MCP server (#28)
- Animated crabs with blinking eyes (#33)
- Multi-claw crab abomination mascot (#2)

### Changed
- Dynamic default branch detection (#7)

### Fixed
- Bounds-checked helper in `action_create_pr` (#9)
- Cursor position reset after table refresh (#13)
- Worktree path existence validation before git status (#8)
- ValueError handling for int() conversions (#5)
- Empty git output handling in worktree parsing (#4)

## Project Links

- **Homepage**: https://github.com/schmug/karkinos
- **Bug Reports**: https://github.com/schmug/karkinos/issues
- **PyPI**: https://pypi.org/project/karkinos/

[unreleased]: https://github.com/schmug/karkinos/compare/v0.2.1...HEAD
[0.2.1]: https://github.com/schmug/karkinos/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/schmug/karkinos/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/schmug/karkinos/releases/tag/v0.1.0
