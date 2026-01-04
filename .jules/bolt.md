## 2024-05-23 - [Memoization of Git Config]
**Learning:** Even fast subprocess calls (like `git symbolic-ref`) add up when called frequently (e.g., in UI loops).
**Action:** Use `functools.lru_cache` for static git configuration values. It reduced check time from ~3ms to ~0.07ms.
