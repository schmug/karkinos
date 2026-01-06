## 2024-01-06 - [Argument Injection in Subprocess]
**Vulnerability:** Git Argument Injection via Branch Names
**Learning:** Even when using `subprocess.run(["cmd", "arg"])` (shell=False), commands like `git` parse arguments starting with `-` as flags. If user input (like a branch name) is passed directly as an argument, a malicious user could supply `-f` or `--upload-pack` to trigger unintended behavior.
**Prevention:**
1. Always use `--` separator for git commands that support it (e.g., `git log -- <branch>`).
2. Validate user input to reject strings starting with `-` if they are intended to be positional arguments.
3. Be aware that some git commands (like `rev-list`) with range syntax `A..B` might not support `--` easily but are safer if `A` is controlled.
