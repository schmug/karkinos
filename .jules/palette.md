## 2024-05-23 - Accessibility in Textual Modals
**Learning:** Textual's `ModalScreen` does not automatically trap focus or set initial focus to content, which can impede keyboard navigation (scrolling) immediately after opening.
**Action:** Always explicit set focus to the main content container in `on_mount` for any `ModalScreen` or `Screen` that presents scrollable content.
