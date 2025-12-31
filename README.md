# Karkinos 🦀

```
            .----------------------------------------.
           /  (\/)  (\/)    (\/)    (\/)    (\/)  (\/) \
          /    \/    \/      \/      \/      \/    \/   \
         |                                               |
         |      (°)                           (°)        |
         |                  KARKINOS                     |
         |                                               |
         |   (\/)     (\/)    __    (\/)     (\/)        |
         |    \/       \/    /  \    \/       \/         |
          \                 | <> |                      /
           \                 \__/                      /
            \           .-----------.                 /
             \         /  (\/)(\/)   \               /
              '-------'    \/  \/     '-------------'
                            \  /
                             \/
```

> *The multi-clawed abomination that helps Claudes work in parallel*

Karkinos enables parallel Claude Code development using git worktrees. Spawn multiple Claude workers, each in their own isolated branch, and monitor their progress from a TUI.

```
(\/)(-_-)(\/)     KARKINOS Worker Monitor     (\/)(-_-)(\/)
┌──────────────────────────────────────────────────────────────────────────┐
│ Worktree           │ Branch           │ Ahead │ Last Commit   │ Activity │
├────────────────────┼──────────────────┼───────┼───────────────┼──────────┤
│ myproject-issue-42 │ fix/issue-42     │ +3    │ fix auth bug  │ idle     │
│ myproject-feat-api │ feat/new-api     │ +1    │ add endpoint  │ M api.py │
└──────────────────────────────────────────────────────────────────────────┘
 Workers: 2  Total Commits: +4                           Updated: 12:34:56
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
| `karkinos watch -s` | Simple text mode (no TUI) |
| `karkinos cleanup` | Remove merged worktrees |
| `karkinos cleanup --dry-run` | Preview what would be removed |

#### Watch Command Options

```bash
karkinos watch              # Full TUI with animated crabs
karkinos watch --spawn      # Open in new terminal (splits in VS Code/Cursor)
karkinos watch --simple     # Simple text mode (works in same terminal as Claude)
karkinos watch --no-crabs   # TUI without crab animations
karkinos watch --speed 0.2  # Faster crab animation (default: 0.4s)
```

## TUI Keybindings

| Key | Action |
|-----|--------|
| `r` | Refresh worker list |
| `c` | Cleanup merged worktrees |
| `p` | Create PR for selected worker |
| `Enter` | Show worker details |
| `l` | Show commit logs |
| `d` | Show diff vs main |
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

## The Mascot

The Karkinos mascot is a **multi-clawed crab abomination** - multiple Claudes merged into a single eldritch crab creature.

**Design Concept:**
- A central crab body with Claude's coral/orange-colored eyes
- Numerous claws extending in all directions (representing parallel workers)
- Each claw is a mini "Clawed" (Claude pun intended)
- Eldritch, slightly unsettling, but friendly
- The `(\/)` symbols represent worker claws
- The `(°)` eyes are Claude's signature orange/coral color

**Image Generation Prompt:**
> A friendly eldritch crab creature with multiple pairs of claws extending in all directions.
> The crab has coral/orange glowing eyes. Each claw tip has a tiny pair of orange eyes,
> representing worker Claudes. The creature has a slight glow and appears to be made of
> code or terminal text. Style: cute horror, ASCII aesthetic, developer-friendly mascot.
> Background: dark terminal green or transparent.

## License

MIT
