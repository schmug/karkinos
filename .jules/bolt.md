## 2024-05-23 - Subprocess Caching
**Learning:** `subprocess.run` has a measurable overhead (~3-4ms per call) even for simple commands.
**Action:** Use `functools.lru_cache` for git commands that return static data (like `git symbolic-ref ... HEAD` for default branch detection) to eliminate this overhead in loops or frequent TUI updates.
