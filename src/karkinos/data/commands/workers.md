# /workers

List all active Claude workers and their git worktrees.

## Instructions

1. List all worktrees:
   ```bash
   git worktree list
   ```

2. For each non-main worktree, show:
   - Branch name
   - Last commit: `git log <branch> --oneline -1`
   - Commits ahead of main: `git rev-list main..<branch> --count`
   - Uncommitted changes: `git -C <worktree-path> status --short`

3. Format as table:
   ```
   | Worktree | Branch | Last Commit | Ahead | Status |
   |----------|--------|-------------|-------|--------|
   | ../artemis-issue-42 | feat/issue-42 | abc123 Fix bug | +2 | clean |
   ```

4. Suggest actions:
   - Workers with commits → "Ready for PR?"
   - Clean worktrees with no commits → "Clean up?"
   - Worktrees with uncommitted changes → "Work in progress"
