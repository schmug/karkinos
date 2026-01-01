## 2024-05-22 - TUI Empty States
**Learning:** TUI apps need explicit "Loading" and "Empty" states just like web apps. A blank table is confusing and makes users wonder if the app is broken or frozen.
**Action:** Always include a `Static` widget with a helpful message/CTA for empty lists, and a loading indicator for async operations. Use CSS classes on a container to toggle visibility cleanly.
