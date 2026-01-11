# Palette's Journal - UX & Accessibility Learnings

## 2024-05-22 - TUI Cleanup Confirmation
**Learning:** Destructive actions in TUI (Text User Interface) applications often lack the friction present in GUI applications (like confirmation modals). Users can accidentally trigger shortcuts (like `c` for cleanup) and lose context or work, even if the action is technically "safe" (merging).
**Action:** Always implement a confirmation modal for bulk or destructive actions in TUI apps to prevent accidental data loss or state changes.
