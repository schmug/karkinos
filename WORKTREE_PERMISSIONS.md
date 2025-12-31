# Claude Code Worktree Permissions Research

This document captures research findings on how Claude Code handles permissions for git worktrees, specifically for the Karkinos worker orchestration system.

## Problem Statement

When an orchestrating Claude tries to read files or run commands in worker worktrees (sibling directories like `../karkinos-issue-5/`), it may hit permission issues or require approval for each worktree path.

## Key Findings

### 1. Permission System Overview

Claude Code uses a hierarchical permission system defined in `~/.claude/settings.json`:

```json
{
  "permissions": {
    "allow": [],     // Rules that allow without prompting
    "ask": [],       // Rules that always prompt
    "deny": [],      // Rules that block (highest priority)
    "additionalDirectories": [],
    "defaultMode": "default"  // or "plan", "acceptEdits", "bypassPermissions"
  }
}
```

**Priority order (highest to lowest):**
1. Managed settings (Enterprise)
2. Local project settings (`.claude/settings.local.json`)
3. Shared project settings (`.claude/settings.json`)
4. User settings (`~/.claude/settings.json`)

### 2. Path Permission Patterns

Claude Code supports four path pattern types:

| Pattern | Syntax | Example |
|---------|--------|---------|
| Absolute path | `//path` | `Read(//Users/alice/secrets/**)` |
| Home directory | `~/path` | `Read(~/Documents/*.pdf)` |
| Relative to settings | `/path` | `Edit(/src/**/*.ts)` |
| Relative to cwd | `path` | `Read(*.env)` |

**Critical:** A pattern like `/Users/alice/file` is NOT absolute—it's relative to your settings file! Use `//Users/alice/file` for true absolute paths.

### 3. Glob Pattern Support

Glob patterns ARE supported for Read/Edit/Glob/Grep rules:
- `**` matches directories recursively
- `*` matches within a directory level
- Examples: `Read(src/**)`, `Edit(/docs/**/*.md)`, `Read(../**)`

**Known Issues (as of 2025):**
- Recursive access with `**` doesn't work reliably in all cases
- Some users report needing approval for individual files despite `parent/**` patterns
- GitHub Issue #6881 documents glob pattern inconsistencies

### 4. Tested Scenarios

#### ✅ Absolute Path Access (WORKS)
```python
# Reading files from sibling worktrees using absolute paths
Read("/Users/cory/karkinos-issue-35/src/karkinos/cli.py")  # ✓ Works
```

#### ✅ Relative Path with `..` (WORKS)
```python
# Using relative paths to access siblings
Read("/Users/cory/karkinos-issue-32/../karkinos-issue-35/src/karkinos/cli.py")  # ✓ Works
```

#### ✅ Git Commands in Worktrees (WORKS)
```bash
# Git commands work with -C flag or cd
git -C /Users/cory/karkinos-issue-35 log --oneline -3  # ✓ Works
cd /Users/cory/karkinos-issue-35 && git status         # ✓ Works
```

### 5. Worker Architecture Impact

Karkinos workers run with `--dangerously-skip-permissions`, which bypasses all permission checks:

```bash
cd "$WORKTREE_PATH" && claude --print --dangerously-skip-permissions "$TASK_DESCRIPTION"
```

**Implications:**
- Workers themselves have no permission restrictions
- Workers operate in their own working directory (the worktree)
- The orchestrator (not workers) is what needs worktree access
- MCP server runs as a subprocess with full system access

### 6. MCP Server Bypass

The Karkinos MCP server (`karkinos-plugin/servers/karkinos-mcp/server.py`) runs as a separate process and:
- Has full filesystem access via Python's `subprocess` and `pathlib`
- Uses `git -C <path>` to operate on any worktree
- Is not subject to Claude Code's permission system
- Can read worker status, diffs, and logs from any worktree

**This is the recommended approach** for the orchestrator to monitor workers.

## Recommendations for Karkinos

### Option 1: MCP Server for All Monitoring (RECOMMENDED)

Extend the existing MCP server with tools for:
- Reading file contents from worktrees
- Comparing diffs between workers and main
- Streaming worker output/logs

**Pros:**
- Already implemented and working
- No permission configuration needed
- Works reliably across all worktrees
- Can be extended with additional tools

**Cons:**
- Requires MCP server to be running
- Slight indirection for simple file reads

### Option 2: Pre-approved Absolute Paths

Add worktree parent directory to `additionalDirectories`:

```json
{
  "permissions": {
    "additionalDirectories": [
      "//Users/cory"
    ],
    "allow": [
      "Read(//Users/cory/karkinos-*/**)",
      "Glob(//Users/cory/karkinos-*/**)",
      "Grep(//Users/cory/karkinos-*/**)"
    ]
  }
}
```

**Pros:**
- Direct file access without MCP
- Works for known worktree patterns

**Cons:**
- Glob patterns may not work reliably
- Requires user to configure settings
- Pattern must match worktree naming convention

### Option 3: Fixed Worktree Location

Create all worktrees in a pre-approved directory:

```bash
# Instead of: ../project-issue-5
# Use: ~/.karkinos-workers/project-issue-5
WORKTREE_PATH="$HOME/.karkinos-workers/${PROJECT}-${BRANCH_SLUG}"
```

Then configure:
```json
{
  "permissions": {
    "additionalDirectories": ["~/.karkinos-workers"],
    "allow": ["Read(~/.karkinos-workers/**)"]
  }
}
```

**Pros:**
- Predictable location
- Single permission entry works for all projects
- Easier to clean up

**Cons:**
- Changes current worktree convention
- Workers farther from main repo in filesystem
- May confuse users expecting sibling directories

### Option 4: Permission Hooks (Advanced)

Use Claude Code hooks for dynamic permission approval:

```json
{
  "hooks": {
    "PermissionRequest": [{
      "matcher": ".*",
      "command": "/path/to/karkinos-permission-hook.sh"
    }]
  }
}
```

The hook script can auto-approve worktree access based on runtime logic.

**Pros:**
- Maximum flexibility
- Can approve any dynamic path

**Cons:**
- Complex to implement
- Requires hook infrastructure
- Security implications need careful consideration

## Summary

| Approach | Reliability | Setup Complexity | Security |
|----------|-------------|------------------|----------|
| MCP Server | ⭐⭐⭐⭐⭐ | Low | Good (isolated) |
| Absolute Paths | ⭐⭐⭐ | Medium | Moderate |
| Fixed Location | ⭐⭐⭐⭐ | Medium | Good |
| Permission Hooks | ⭐⭐⭐⭐ | High | Depends |

**Primary Recommendation:** Continue using and extending the MCP server for orchestrator-to-worker communication. The MCP architecture already solves the permission problem by operating outside Claude Code's permission system.

**Secondary Recommendation:** For users who need direct file access, document the permission patterns they can add to their settings, while noting the reliability caveats.

## Testing Notes

Tested on: macOS Darwin 24.6.0
Claude Code version: Claude Opus 4.5 (claude-opus-4-5-20251101)
Date: 2025-12-31

### Verified Working:
- [x] Absolute path reads to sibling worktrees
- [x] Relative path reads with `../` prefix
- [x] Git commands with `-C` flag in worktrees
- [x] MCP server access to all worktrees
- [x] Workers with `--dangerously-skip-permissions`

### Known Issues:
- [ ] Glob patterns with `**` may require individual approvals
- [ ] `additionalDirectories` with globs not fully tested
- [ ] Hook-based permissions not tested
