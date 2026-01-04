# AGENTS.md

This file provides guidance for orchestrating parallel Claude subagents using Karkinos. It covers conflict prevention, the staging branch workflow, and best practices for spawning workers.

## Staging Branch Workflow

Karkinos uses a **staging branch** as an integration layer between worker branches and main:

```
main ← staging ← worker branches
```

### Branch Hierarchy

1. **main**: Production-ready code. Only receives PRs from staging after CI passes.
2. **staging**: Integration branch. All worker PRs target this branch. Used for testing combined changes.
3. **worker branches**: Feature/fix branches created by subagents, always branching from staging.

### Setup

Ensure the staging branch exists before spawning workers:

```bash
# Create staging branch from main (if it doesn't exist)
git fetch origin
git checkout -b staging origin/main 2>/dev/null || git checkout staging
git push -u origin staging
```

### Merging to Main

When all workers have completed and CI is green on staging:

```bash
# Create PR from staging to main
gh pr create --base main --head staging --title "Release: merge staging to main" --body "$(cat <<'EOF'
## Summary
Merge integrated changes from staging branch.

## Included Changes
- List of merged worker PRs

## CI Status
All checks passing on staging.
EOF
)"
```

## Conflict Prevention Strategy

**CRITICAL**: Before spawning any subagent, the orchestrator MUST verify there are no file conflicts with existing workers.

### File Tracking

The orchestrator maintains awareness of which files each worker is modifying:

```bash
# Check files being modified by existing workers
for worktree in $(git worktree list --porcelain | grep "^worktree" | cut -d' ' -f2 | grep -v "$(pwd)$"); do
  echo "=== Worker: $worktree ==="
  git -C "$worktree" diff --name-only staging 2>/dev/null || echo "(no changes yet)"
done
```

### Pre-Spawn Verification

Before spawning a new worker, the orchestrator MUST:

1. **Identify target files**: Analyze the task to determine which files will likely be modified
2. **Check existing workers**: Query all active worktrees for their modified files
3. **Detect conflicts**: Compare target files against active worker files
4. **Block or queue**: If conflicts exist, either wait for the conflicting worker to complete or reject the spawn

### Verification Checklist

```markdown
## Pre-Spawn Checklist

- [ ] Staging branch is up to date with main
- [ ] Identified files that new worker will modify
- [ ] Checked all active worktrees for file conflicts
- [ ] No overlap detected with existing workers
- [ ] Worker can proceed safely
```

### Conflict Detection Script

Use this to check for conflicts before spawning:

```bash
#!/bin/bash
# Check if files conflict with existing workers

TARGET_FILES="$@"  # Files the new worker will modify

conflict_found=false
for worktree in $(git worktree list --porcelain | grep "^worktree" | cut -d' ' -f2 | grep -v "$(pwd)$"); do
  worker_files=$(git -C "$worktree" diff --name-only staging 2>/dev/null)
  for target in $TARGET_FILES; do
    if echo "$worker_files" | grep -q "^${target}$"; then
      echo "CONFLICT: $target is being modified in $worktree"
      conflict_found=true
    fi
  done
done

if [ "$conflict_found" = true ]; then
  echo "Cannot spawn worker - file conflicts detected"
  exit 1
fi
echo "No conflicts - safe to spawn worker"
```

## Orchestrator Responsibilities

The main Claude (orchestrator) has these responsibilities:

### 1. Task Analysis

Before delegating to a worker:
- Understand the full scope of the task
- Identify all files that will likely be modified
- Determine if the task can be parallelized or must be sequential

### 2. Worker Spawning

When spawning workers:
- Always branch from `staging`, not `main`
- Verify no file conflicts with active workers
- Provide clear, scoped task descriptions
- Track which files each worker owns

### 3. Integration Management

After workers complete:
- Review worker PRs before merging to staging
- Run integration tests on staging
- Resolve any merge conflicts in staging
- Create staging → main PR when ready

### 4. Conflict Resolution

If conflicts arise:
- Stop spawning new workers to affected files
- Wait for conflicting workers to complete
- Merge in order of completion
- Rebase remaining workers if necessary

## Worker Guidelines

Workers should follow these practices:

### Scope Discipline

- Only modify files within the assigned scope
- Do not refactor unrelated code
- Keep changes focused and minimal

### Commit Practices

- Make atomic commits
- Reference the task/issue in commit messages
- Commit frequently to show progress

### Branch Management

```bash
# Workers always branch from staging
git checkout staging
git pull origin staging
git checkout -b feat/my-feature

# When done, PR targets staging
gh pr create --base staging --head feat/my-feature
```

## Example Workflow

### Orchestrator spawns parallel workers:

```
Task: "Add user authentication and improve error handling"

Orchestrator analysis:
- Auth feature: touches src/auth/*, src/api/middleware.py
- Error handling: touches src/errors/*, src/utils/logger.py
- NO FILE OVERLAP → safe to parallelize

Spawn Worker 1: "Implement user authentication"
  → Branch: feat/user-auth
  → Files: src/auth/*, src/api/middleware.py

Spawn Worker 2: "Improve error handling"
  → Branch: feat/error-handling
  → Files: src/errors/*, src/utils/logger.py
```

### Orchestrator detects conflict:

```
Task: "Add logging to auth module and refactor auth flow"

Orchestrator analysis:
- Logging task: touches src/auth/login.py, src/utils/logger.py
- Refactor task: touches src/auth/login.py, src/auth/session.py
- CONFLICT: src/auth/login.py → must be sequential

Decision: Run refactor first, then logging task after completion
```

## Status Tracking

Track worker status in `.claude/workers.json`:

```json
{
  "workers": [
    {
      "id": "worker-1",
      "branch": "feat/user-auth",
      "base": "staging",
      "files": ["src/auth/*", "src/api/middleware.py"],
      "status": "in_progress",
      "spawned": "2024-01-15T10:30:00Z"
    }
  ],
  "staging_status": {
    "last_sync_with_main": "2024-01-15T10:00:00Z",
    "pending_prs": 2,
    "ci_status": "passing"
  }
}
```

## Commands Reference

```bash
# List active workers and their files
karkinos list --files

# Watch workers with conflict warnings
karkinos watch

# Check for conflicts before spawning
karkinos check-conflicts <file1> <file2> ...

# Cleanup merged worktrees
karkinos cleanup

# Sync staging with main
git checkout staging && git merge main && git push
```

## Best Practices Summary

1. **Always use staging**: Never branch directly from main for worker tasks
2. **Verify before spawning**: Check file conflicts for every new worker
3. **Scope tasks carefully**: Design tasks to minimize file overlap
4. **Sequential when needed**: Don't force parallelization when files conflict
5. **Integrate frequently**: Merge completed workers to staging promptly
6. **Test on staging**: Run full CI before promoting to main
7. **Track everything**: Maintain awareness of all active workers and their files
