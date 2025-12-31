# /pr-worker

Spawn a Claude worker to address PR feedback or fix CI.

## Arguments
- `$ARGUMENTS` - PR number, optionally with flags (e.g., `123` or `123 --ci`)

## Instructions

1. Parse arguments for PR number and flags (`--review` or `--ci`)

2. Fetch PR details:
   ```bash
   gh pr view <number> --json number,title,headRefName,reviews,comments,statusCheckRollup
   ```

3. Check if worktree exists for this branch, or create one:
   ```bash
   git worktree add "../artemis-pr-<number>" "<headRefName>"
   ```

4. Build prompt based on mode:

   **For --review (or default):**
   - Fetch review comments: `gh api repos/{owner}/{repo}/pulls/<number>/comments`
   - Prompt worker to address each unresolved comment

   **For --ci:**
   - Get failed checks: `gh pr checks <number>`
   - Get failure logs: `gh run view <run-id> --log-failed`
   - Prompt worker to fix CI failures

5. Spawn worker:
   ```bash
   cd "../artemis-pr-<number>" && claude --print --dangerously-skip-permissions "<prompt>"
   ```

6. After completion, offer to push:
   ```bash
   git push origin <branch>
   ```
