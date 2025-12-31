---
name: worker
description: Spawn a Claude worker in an isolated git worktree for parallel development. Use when you need to work on a task in isolation without affecting current work.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# Worker Skill

Spawn a Claude worker in an isolated git worktree.

## Usage

```
/worker <branch-name> <task description>
```

## Examples

```
/worker feat/add-logging Add structured logging to the supervisor module
/worker fix/auth-bug Fix the authentication bypass in the API
/worker refactor/cleanup Refactor the instance manager for clarity
```

## Instructions

When the user invokes `/worker`, follow these steps:

### 1. Parse Arguments

Extract the branch name (first argument) and task description (remaining text).

### 2. Create Worktree

```bash
# Get project name for worktree prefix
PROJECT=$(basename $(git rev-parse --show-toplevel))
WORKTREE_PATH="../${PROJECT}-$(echo $BRANCH | tr '/' '-')"

# Create the worktree with a new branch
git worktree add "$WORKTREE_PATH" -b "$BRANCH"
```

### 3. Spawn Worker Claude

Run a Claude instance in the worktree with full autonomy:

```bash
cd "$WORKTREE_PATH" && claude --print --dangerously-skip-permissions "$TASK_DESCRIPTION"
```

### 4. Report Results

After the worker completes:
1. Show the worker's output
2. Show any commits made: `git log $BRANCH --oneline -5`
3. Ask if user wants to:
   - Create a PR from the worker's branch
   - Continue working (spawn another worker command)
   - Clean up the worktree

## Important Notes

- Workers have full autonomy (`--dangerously-skip-permissions`)
- Each worker gets its own branch - no conflicts with main work
- Workers can make commits but should NOT push or create PRs directly
- The orchestrator (main Claude) handles PR creation after review
- Use `git worktree list` to see active workers
- Use `git worktree remove <path>` to clean up
