---
logged: 2026-03-16
context: Workshop on multi-round orchestration — observed that maintenance logging is a special case of a general "write structured docs" behavior.
---

The current maintenance log behavior in `tab.md` writes structured markdown files to `docs/maintenance/`. This is useful but narrow — the same pattern (structured doc with frontmatter, written to a known location, announced to the user) could serve decision records, design rationale, meeting notes, and more.

Consider extracting a `/document` skill that generalizes this. Maintenance notes become one use case, not the whole feature. The maintenance log section in `tab.md` could then be simplified to reference the skill rather than describing the full behavior inline.
