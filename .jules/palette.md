## 2024-12-XX - [Modal Focus Management in Textual]
**Learning:** Textual's `ModalScreen` does not automatically set focus to its content on mount. This forces keyboard users to Tab manually before they can interact with the content (e.g., scroll).
**Action:** Always implement `on_mount` in `ModalScreen` subclasses and explicitly call `.focus()` on the main content widget (e.g., `self.query_one("#content").focus()`).

## 2024-12-XX - [Empty State Guidance]
**Learning:** Empty states are prime real estate for onboarding. Generic instructions (like raw git commands) are less helpful than specific application commands (like `/worker`) when the user is operating within a specific toolchain.
**Action:** Tailor empty state messages to the specific workflow of the user, suggesting the most efficient path forward using the tool's own commands.
