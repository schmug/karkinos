## 2024-11-06 - Argument Injection in Git Commands
**Vulnerability:** Argument Injection (CWE-88) in `karkinos-mcp/server.py`.
**Learning:** Python `subprocess.run(list)` prevents Shell Injection but NOT Argument Injection. If an untrusted string starts with `-`, the target program (e.g., `git`) interprets it as a flag.
**Prevention:**
1. Validate inputs (e.g., ensure branch names don't start with `-`).
2. Use `--` separator in commands (e.g., `git push origin -- {branch}`).

## 2024-12-04 - Strict Branch Name Validation
**Vulnerability:** Weak input validation in `validate_branch_name` (only checked leading `-`).
**Learning:** Git branch names have complex rules (`man git-check-ref-format`). A block-list approach (blocking `-`) is insufficient as it misses directory traversal (`..`) or confusing characters (`:`, `^`, `~`).
**Prevention:** Use a strict allow-list regex (`^[a-zA-Z0-9/_.-]+$`) for branch names in automation tools to prevent Argument Injection and Logic Errors.
