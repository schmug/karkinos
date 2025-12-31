# /issue-worker

Spawn a Claude worker to handle a GitHub issue.

## Arguments
- `$ARGUMENTS` - Issue number (e.g., `42`)

## Instructions

1. Fetch issue details:
   ```bash
   gh issue view $ARGUMENTS --json number,title,body,labels,comments
   ```

2. Generate branch name from issue:
   - Bug → `fix/issue-<num>-<slug>`
   - Feature → `feat/issue-<num>-<slug>`

3. Create worktree:
   ```bash
   git worktree add "../artemis-issue-$ARGUMENTS" -b "$BRANCH"
   ```

4. Build prompt with issue context and spawn worker:
   ```bash
   cd "../artemis-issue-$ARGUMENTS" && claude --print --dangerously-skip-permissions "
   You are working on GitHub Issue #<number>: <title>

   ## Issue Description
   <body>

   ## Your Task
   1. Implement the necessary changes
   2. Write tests if applicable
   3. Commit with message referencing the issue
   "
   ```

5. Report results and offer to create PR:
   ```bash
   gh pr create --title "<title>" --body "Closes #<number>"
   ```
