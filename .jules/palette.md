## 2024-05-22 - Reusable Confirmation Dialog
**Learning:** Destructive actions in TUI were unprotected. Created a reusable `ConfirmationScreen` component inheriting from `ModalScreen`.
**Action:** Use `ConfirmationScreen` for any future destructive actions (delete, force push, etc) in the TUI.
