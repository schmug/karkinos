# /worker-cleanup

Remove completed worker worktrees and their branches.

## Arguments
- `$ARGUMENTS` - Optional: specific worktree path, branch name, or `--all-merged`

## Instructions

### If specific worktree/branch provided:

1. Check for uncommitted changes:
   ```bash
   git -C <worktree> status --porcelain
   ```
   Warn if dirty.

2. Check if branch is merged:
   ```bash
   git branch --merged main | grep <branch>
   ```
   Warn if unmerged.

3. Remove worktree and branch:
   ```bash
   git worktree remove <path>
   git branch -d <branch>  # -D if unmerged and user confirms
   ```

### If `--all-merged`:

1. Find all merged branches with worktrees
2. Remove each worktree and delete branch
3. Report what was cleaned

### If no arguments:

1. List worktrees with their status (merged/unmerged, clean/dirty)
2. Ask user which to clean up

## Safety
- Never remove main worktree
- Warn before removing worktrees with uncommitted changes
- Keep unmerged branches unless user confirms deletion
