# /worker

Spawn a Claude worker in an isolated git worktree.

## Arguments
- `$ARGUMENTS` - Branch name and task description (e.g., `feat/add-logging Add logging to supervisor`)

## Instructions

1. Parse the first word as branch name, rest as task description
2. Create worktree:
   ```bash
   BRANCH="<first-arg>"
   WORKTREE="../artemis-$(echo $BRANCH | tr '/' '-')"
   git worktree add "$WORKTREE" -b "$BRANCH"
   ```
3. Spawn autonomous Claude worker:
   ```bash
   cd "$WORKTREE" && claude --print --dangerously-skip-permissions "<task-description>"
   ```
4. Show results:
   - Worker output
   - Commits made: `git log $BRANCH --oneline -5`
   - Files changed: `git diff main...$BRANCH --stat`
5. Ask: Create PR? Continue working? Clean up?
