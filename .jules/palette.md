# Palette's Journal

## 2024-05-22 - Destructive Action Confirmation
**Learning:** Destructive actions (like deleting branches/worktrees) must always have a confirmation step, even if the action seems "safe" (like cleaning merged branches). Users may not realize which branches are considered "merged".
**Action:** Always wrap destructive `action_*` methods in the TUI with a `ConfirmationScreen` modal. Pre-calculate the impact (e.g., "Delete 3 items?") to give users context before they confirm.
