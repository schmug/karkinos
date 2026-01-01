## 2024-10-24 - Path Traversal in MCP Server
**Vulnerability:** The `read_file` function in the MCP server allowed reading files outside the worktree using `../` path traversal.
**Learning:** `Path.resolve()` is crucial for security when dealing with user-supplied paths. Simply concatenating paths is not enough.
**Prevention:** Always resolve paths and check if the resulting path starts with the expected base directory using `path in base.parents` or similar robust checks.
