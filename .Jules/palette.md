## 2024-05-23 - Empty States
**Learning:** Textual's `DataTable` lacks a built-in empty state, which can leave users confused when no data is present.
**Action:** Use a `Container` with CSS toggling (`.empty` class) to switch between the table and a `Static` widget containing helpful guidance. This pattern is reusable for any list/table view.
