## 2024-05-23 - Sync Status Clarity
**Learning:** Users managing multiple worktrees often lose track of divergence (commits behind main). Showing only "Ahead" commits is insufficient for maintenance.
**Action:** Implemented a split "Sync" status showing both `+ahead` and `-behind` counts (e.g., `+2 -5`) using green/red color coding. This allows users to instantly spot stale branches that need rebasing. The `[dim]sync[/]` state provides positive reinforcement for clean states.
