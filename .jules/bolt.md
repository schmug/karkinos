## 2024-05-23 - Subprocess Overhead in TUI Loops
**Learning:** Frequent `subprocess.run` calls (even simple ones like `git symbolic-ref`) in TUI render loops or frequent refreshes create massive overhead (~4ms per call vs ~0.01ms cached).
**Action:** Always profile `subprocess` calls in hot paths and memoize static or slowly changing values.
