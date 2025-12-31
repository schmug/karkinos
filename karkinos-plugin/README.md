# Karkinos Claude Code Plugin

A Claude Code plugin for managing parallel Claude workers with git worktrees.

## Features

- **MCP Tools**: Permission-free access to worker management
- **Skills**: Bundled worker/issue-worker skills
- **Commands**: Slash commands for worker operations

## Requirements

- Python 3.10+
- Git
- GitHub CLI (`gh`) for PR creation

## Installation

### Option 1: Add Plugin Directory

```bash
# Clone the repo
git clone https://github.com/schmug/karkinos.git

# Tell Claude Code to load the plugin
claude --plugin-dir /path/to/karkinos/karkinos-plugin
```

### Option 2: Symlink to Plugins Directory

```bash
# Symlink for persistent installation
ln -s /path/to/karkinos/karkinos-plugin ~/.claude/plugins/karkinos
```

Restart Claude Code after installing. The MCP server will start automatically.

## MCP Tools

| Tool | Description |
|------|-------------|
| `karkinos_list_workers` | List all active workers with status |
| `karkinos_get_worker_details` | Get commits and diff stats for a worker |
| `karkinos_cleanup_workers` | Remove merged worktrees |
| `karkinos_create_pr` | Create PR for a worker branch |
| `karkinos_update_branches` | Rebase/merge main into worker branches |
| `karkinos_read_file` | Read a file from a worker worktree |
| `karkinos_get_diff` | Get full diff for a worker vs main |

## Skills Included

- `/worker` - Spawn a worker in isolated worktree
- `/issue-worker` - Work on a GitHub issue
- `/pr-worker` - Address PR feedback
- `/workers` - List active workers
- `/worker-cleanup` - Clean up finished workers

## Usage

Once installed, Claude can use the MCP tools directly:

```
"List my active workers"
→ Uses karkinos_list_workers tool

"Show details for the fix/issue-42 branch"
→ Uses karkinos_get_worker_details tool

"Clean up merged worktrees"
→ Uses karkinos_cleanup_workers tool
```

## Development

Test the MCP server locally:

```bash
echo '{"jsonrpc":"2.0","id":1,"method":"initialize"}' | python servers/karkinos-mcp/server.py
echo '{"jsonrpc":"2.0","id":2,"method":"tools/list"}' | python servers/karkinos-mcp/server.py
```
