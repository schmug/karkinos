## 2024-05-23 - Git Subprocess Overhead
**Learning:** `git symbolic-ref` takes ~3.5ms per call. While small, this adds up significantly in tight loops (like TUI refresh cycles) or when called repeatedly for multiple items.
**Action:** Use `functools.lru_cache` for static git info like default branch name to eliminate this overhead entirely (~0.0003ms cached).
