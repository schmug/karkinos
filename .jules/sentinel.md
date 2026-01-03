## 2024-11-06 - Argument Injection in Git Commands
**Vulnerability:** Argument Injection (CWE-88) in `karkinos-mcp/server.py`.
**Learning:** Python `subprocess.run(list)` prevents Shell Injection but NOT Argument Injection. If an untrusted string starts with `-`, the target program (e.g., `git`) interprets it as a flag.
**Prevention:**
1. Validate inputs (e.g., ensure branch names don't start with `-`).
2. Use `--` separator in commands (e.g., `git push origin -- {branch}`).

## 2024-11-06 - Argument Injection in Git Log (CLI/TUI)
**Vulnerability:** `git log {branch}` calls in `cli.py` and `tui.py` were vulnerable to flag injection if `branch` started with `-`.
**Learning:** `git log` treats arguments after `--` as paths, not revisions. This makes standard `--` mitigation ineffective for revision arguments.
**Prevention:** Use `--end-of-options` to separate flags from revisions in `git log` (and other commands that treat post-`--` args as paths). Example: `git log --end-of-options {branch}`.
