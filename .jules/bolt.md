## 2024-05-22 - TUI Polling Loop Optimization
**Learning:** Polling loops in TUIs magnify the cost of even fast subprocess calls. `git symbolic-ref` takes ~3ms, but calling it repeatedly in a loop (e.g. per-worker status check) wastes CPU and IO.
**Action:** Memoize static configuration values (like default branch) that are unlikely to change during runtime. Use `functools.lru_cache` for functions that fetch static git config.
