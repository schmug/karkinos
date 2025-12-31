# Karkinos Claude Code Plugin

A Claude Code plugin for managing parallel Claude workers with git worktrees.

## Features

- **MCP Tools**: Permission-free access to worker management
- **Skills**: Bundled worker/issue-worker skills
- **Commands**: Slash commands for worker operations

## MCP Tools

| Tool | Description |
|------|-------------|
| `karkinos_list_workers` | List all active workers with status |
| `karkinos_get_worker_details` | Get commits and diff for a worker |
| `karkinos_cleanup_workers` | Remove merged worktrees |
| `karkinos_create_pr` | Create PR for a worker branch |

## Installation

### From Local Directory

```bash
# Copy plugin to Claude Code plugins directory
cp -r karkinos-plugin ~/.claude/plugins/karkinos

# Or symlink for development
ln -s $(pwd)/karkinos-plugin ~/.claude/plugins/karkinos
```

### Enable the Plugin

Restart Claude Code after installing. The MCP server will start automatically.

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

## Skills Included

- `/worker` - Spawn a worker in isolated worktree
- `/issue-worker` - Work on a GitHub issue
- `/pr-worker` - Address PR feedback
- `/workers` - List active workers
- `/worker-cleanup` - Clean up finished workers

## Development

Test the MCP server locally:

```bash
echo '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' | python servers/karkinos-mcp/server.py
```
