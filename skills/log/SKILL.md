---
name: log
description: "Log deferred work to docs/maintenance/. Use when something surfaces that doesn't need doing right now — Tab or the user identifies work that's out of scope, the user says 'we'll handle that later' / 'not now' / 'next pass' / 'parking that', or a workshop or review surfaces a known gap that isn't being addressed immediately. Also triggers on /log."
argument-hint: "[what to log]"
---

Log deferred work to `docs/maintenance/` so the team has a shared record of what's waiting.

## How to log

1. **Tell the user first.** Before writing anything, say what you're logging and why — e.g., "I'll log that auth token rotation issue to `docs/maintenance/` so it doesn't get lost."
2. **Write one file per item** to `docs/maintenance/`, named descriptively with lowercase kebab-case (e.g., `auth-token-rotation.md`).
3. **File format:**

```markdown
---
logged: YYYY-MM-DD
context: (what conversation or task surfaced this)
---

What needs doing, why it was deferred, and any relevant context for whoever picks it up.
```

## What NOT to do

- **Don't clean up maintenance files.** That's the team's call, not Tab's.
- **Don't log things that belong in memory.** Memory is for Tab's future self. Maintenance docs are for humans on the team.
- **Don't log active work.** If it's in the current plan or task list, it's not deferred — it's in progress.
