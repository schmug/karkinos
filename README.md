# Karkinos 🦀

> *The crab that helps Claudes work in parallel*

Karkinos enables parallel Claude Code development using git worktrees. Spawn multiple Claude workers, each in their own isolated branch, and monitor their progress from a TUI.

```
┌─ Karkinos Workers ───────────────────────────────────────────┐
│ Worktree              │ Branch                │ Ahead │ Status │
├───────────────────────┼───────────────────────┼───────┼────────┤
│ myproject-issue-42    │ fix/issue-42-auth     │ +3    │ clean  │
│ myproject-feat-api    │ feat/new-api          │ +1    │ modified│
└──────────────────────────────────────────────────────────────┘
 Workers: 2  Total Commits: +4                Updated: 12:34:56
```

## How It Works

1. **You** talk to the orchestrator Claude in your main terminal
2. **Orchestrator** spawns worker Claudes in git worktrees
3. **Workers** operate autonomously on isolated branches
4. **TUI** monitors all workers in a separate terminal pane
5. **Orchestrator** reviews results and creates PRs

```
You (human)
└── Claude (orchestrator)
    ├── /worker feat/auth "Add OAuth support"
    │   └── Worker Claude in ../myproject-feat-auth/
    ├── /issue-worker 42
    │   └── Worker Claude in ../myproject-issue-42/
    └── /workers
        └── Shows status of all active workers
```

## Installation

```bash
# Install with uv
uv tool install karkinos

# Or with pip
pip install karkinos
```

## Quick Start

### 1. Initialize in your project

```bash
cd your-project
karkinos init
```

This adds Claude Code skills and commands to `.claude/`.

### 2. Start the TUI monitor (optional, separate terminal)

```bash
karkinos watch
```

### 3. Use Claude with worker commands

```bash
claude
```

Then in Claude:
```
/worker feat/new-feature Add a cool new feature
/issue-worker 42
/workers
/worker-cleanup
```

## Commands

### Slash Commands (in Claude)

| Command | Description |
|---------|-------------|
| `/worker <branch> <task>` | Spawn worker in new worktree |
| `/issue-worker <num>` | Work on GitHub issue |
| `/pr-worker <num>` | Address PR feedback |
| `/workers` | List active workers |
| `/worker-cleanup` | Remove finished worktrees |

### CLI Commands

| Command | Description |
|---------|-------------|
| `karkinos init` | Add skills/commands to project |
| `karkinos list` | List active workers |
| `karkinos watch` | Launch TUI monitor |
| `karkinos cleanup` | Remove merged worktrees |

## TUI Keybindings

| Key | Action |
|-----|--------|
| `r` | Refresh worker list |
| `c` | Cleanup merged worktrees |
| `p` | Create PR for selected worker |
| `q` | Quit |

## How Workers Operate

Each worker:
- Runs in an isolated git worktree
- Has its own branch (no conflicts)
- Uses `claude --print --dangerously-skip-permissions`
- Can make commits but doesn't push
- Reports back to the orchestrator

The orchestrator (your main Claude session):
- Reviews worker output
- Decides next steps
- Creates PRs when ready
- Cleans up worktrees

## Requirements

- Git 2.17+ (for worktree support)
- Claude Code CLI (`claude`)
- Python 3.10+

## Why "Karkinos"?

In Greek mythology, Karkinos was a crab sent by Hera to help the Hydra fight Heracles. Though small, it tried to help - and was immortalized in the stars as the constellation Cancer.

Like its namesake, Karkinos coordinates many small helpers (Claude workers) to tackle larger tasks.

## License

MIT
