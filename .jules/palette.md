## 2024-03-21 - [Icon Status Indicators]
**Learning:** Replacing text codes (pass/fail/ok) with Unicode icons (✔/✘/⟳/●) in CLI tables significantly improves scan-ability and aesthetic appeal without adding new dependencies or complex UI components. It allows users to assess status at a glance.
**Action:** Prefer standard Unicode icons for status indicators in TUI applications, but ensure fallback or font support is considered if targeting older environments (though modern terminals handle these well).
