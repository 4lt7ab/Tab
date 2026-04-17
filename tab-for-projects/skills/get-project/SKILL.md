---
name: get-project
description: Pull a token-budgeted snapshot of the current project into the session — health, blockers, in-progress and upcoming tasks, recent activity, and linked documents. Use at the start of a work session to orient, or after a break to see what changed. Triggers on `/get-project` and phrases like "where was I", "what's the state of this project", "catch me up on X".
argument-hint: "[--focus=full|blockers|active_work] [--since=<ISO timestamp>]"
---

The orientation skill. At the start of a session, after a gap, or when switching projects, the user wants a fast, accurate read of where things stand. This skill resolves the project, pulls a tier-prioritized snapshot via the MCP, and presents it in a form that's useful for deciding what to do next.

## Trigger

**When to activate:**
- User invokes `/get-project`, optionally with `--focus` or `--since`.
- User says "where was I", "what's the state of this project", "catch me up", "what changed since yesterday".
- Session just started and the user's first action is project work — offer proactively.

**When NOT to activate:**
- User wants to find a specific doc or task — use `/search`.
- User wants to create new work — use `/plan-project` or `/fix`.
- User wants to execute — use `/develop`.

## Requires

- **MCP:** `tab-for-projects` — for `get_project_context`, project resolution.

## Behavior

### 1. Resolve which project this run targets:

1. Explicit `--project=<id or title>` argument wins.
2. Read `.tab-project` at repo root if present.
3. Parse git remote `origin`; exact repo-name match against project titles is high confidence.
4. Match cwd basename and parent segments against project titles.
5. Fall back to most recently updated plausible project. Never sole signal.

If confidence is below **confident**, surface the top 2–3 candidates and ask. State the resolved project in the opening line.

### 2. Pick the right context call

Call `get_project_context` with:

- `project_id` — resolved above.
- `focus` — `full` (default), `blockers` (emphasize what's stuck), or `active_work` (emphasize in-progress + next-up).
- `since` — when provided, the MCP adds a `changes_since` section at highest priority. Use this when the user says "what changed since X" or when the skill was last run recently in the same session.
- `max_tokens` — 4000 default is fine for most calls. Bump to 8000 if the user asked for a deep read.

### 3. Present the snapshot

Reshape the MCP response into a human-readable summary. Sections in order of relevance:

1. **Header** — project name, one-line summary, total tasks / done / todo / blocked counts.
2. **Changes since** — if `since` was used, show this first. What moved.
3. **Blockers** — any blocked tasks, what they're waiting on.
4. **In progress** — what's actively being worked, with ULIDs for quick reference.
5. **Up next** — top todo tasks, preferably filtered to ready ones.
6. **Recent activity** — last 5–10 meaningful events. Skip noise (trivial field updates).
7. **Linked docs** — key reference docs, with titles and folders. Don't dump content.

Keep it skimmable. The user is orienting, not reading a report.

### 4. Close with a next-step suggestion

End with one concrete suggestion grounded in what the snapshot showed:

- 3+ blocked tasks → suggest `/manage-backlog`.
- Healthy ready backlog → suggest `/develop`.
- Lots of unscored tasks → suggest `/manage-backlog`.
- Clean and quiet → say so; suggest the user say what they want to work on.

One suggestion, matched to the state. Not a menu.

## Output

A compact, scannable project snapshot ending in a single next-step suggestion. Example:

```
Project: Tab (01KN6H…)
Turns Claude Code into a thinking partner + project management suite.

121 tasks — 99 done, 22 archived, 0 todo, 0 blocked.

Recent activity:
  • 2026-04-17 — Conventions: Task Readiness Bar (created)
  • 2026-04-17 — Conventions: Project Inference (created)
  • 2026-04-16 — Template: Skill Headers (updated)

Linked reference docs: Best Practices: Agents & Skills, Architecture Decisions,
Conventions: Plugin Structure, Prompt Quality Conventions, Template: Agentic Headers,
Template: Skill Headers, Conventions: Project Inference, Conventions: Task Readiness Bar.

Backlog is clean. Next move is on you — planning new work (/plan-project) or
filing a one-off (/fix).
```

## Principles

- **Orient, don't overwhelm.** The user wants context, not a data dump. Let the MCP's tiered response do the trimming; don't add more.
- **Recent matters most.** Tasks and docs touched today are more interesting than last month's.
- **State the project name every run.** Cheap correction signal if inference went wrong.
- **One next step, not a menu.** The snapshot usually implies the next move; say it.

## Constraints

- **Read-only.** This skill never writes to the MCP.
- **No writes below confident project inference.** Doesn't apply here (read-only), but if inference is ambiguous, still ask rather than guess — wrong-project context wastes the user's time.
- **No full document content.** Cite titles and folders; the user uses `/search` or `get_document` to read.
- **Don't restate everything in the MCP response.** Summarize. The snapshot is there to cue action, not to mirror the database.
