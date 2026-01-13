## 2026-01-13 - Subprocess Overhead in TUI
**Learning:** Even fast subprocess calls (like `git symbolic-ref`, ~3ms) cause noticeable UI latency if called synchronously on the main thread in a TUI loop or frequent interaction.
**Action:** Memoize invariant git queries like `get_default_branch` using `lru_cache`.
