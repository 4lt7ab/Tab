---
name: feature
description: Capture new feature work onto the backlog — a single task for a small idea, or a decomposed backlog for a bigger one. Scales rigor to what the input needs: zero interview when context is complete, a short interview (3–5 questions) when acceptance is unclear, targeted web research when the objective touches unfamiliar territory, dependency wiring when tasks have natural ordering. Triggers on `/feature` and phrases like "file this as a feature", "plan out the work for X", "build me a backlog for Y", "break this down into tasks".
argument-hint: "[idea or objective]"
---

The "new work" skill. The user has an idea — small or large, sharp or fuzzy — and wants it landed on the backlog as ready-to-execute tasks. This skill reads the conversation, figures out what the idea actually needs (one task? several? interview? research?), shapes the work, confirms once, and writes.

## Design note

Earlier versions split this into two skills: `/feature` for the fast path (no research, no interview) and `/plan-project` for the heavier path (interview + research + decomposition + deps). That split forced the user to choose rigor up front, often wrong. This skill picks the right rigor from signals in the input instead:

- **Interview** activates when the proposed tasks can't all meet the readiness bar from the conversation alone. Bounded at 3–5 questions; never a requirements workshop.
- **Research** activates when the objective touches unfamiliar territory the conversation didn't resolve. One to three focused searches.
- **Dependency wiring** activates when the decomposition has natural ordering.

All three phases are skipped when the conversation already resolved them. The ceiling is full planning; the floor is a one-line idea → one task.

## Trigger

**When to activate:**
- User invokes `/feature` optionally followed by the idea inline.
- User says "file this as a feature", "add a feature task for", "plan out the work for X", "build me a backlog for Y", "break this down into tasks", "what would it take to ship Z".
- User has been describing feature work in conversation and wants it landed without manual filing.

**When NOT to activate:**
- User wants to file a single small bug or drive-by cleanup — use `/fix`.
- User is still thinking and hasn't committed to any shape — use `/think`.
- User wants to groom existing tasks — use `/backlog`.
- User wants to execute — use `/work`.

## Requires

- **MCP:** `tab-for-projects` — for project resolution, task creation, dependency wiring.
- **MCP (preferred):** `exa` — `web_search_exa` and `web_fetch_exa` for research. Better results than native search for technical topics.
- **Tool (fallback):** `WebSearch` / `WebFetch` — used only when the `exa` MCP is unavailable.

## Behavior

### 1. Resolve the project

Follow the shared Project Inference convention:

1. Explicit `project:<id or title>` argument wins.
2. Read `.tab-project` at repo root if present.
3. Parse git remote `origin`; exact repo-name match is high confidence.
4. Match cwd basename and parent segments against project titles.
5. Fall back to most recently updated plausible project. Never sole signal.

Below **confident**, ask or stop. No writes below confident. State the resolved project in the opening line so the user can catch a bad inference before tasks are written.

### 2. Read the invocation and the surrounding conversation

The user's words are the starting point. Pull:

- The idea or objective itself.
- Scope hints — what's in, what's out.
- Acceptance hints — what "done" looks like.
- Constraints already named — decisions, dependencies, deadlines.

Do not search the codebase.

### 3. Decide the shape

Is this one task or several?

- **One task** — a single coherent change a commit (or small PR) could deliver.
- **Several tasks** — the idea decomposes along seams the user already named (separate surfaces, separate milestones, separate concerns). If you have to invent the split, it's probably one task.

Sizing: one task = one PR-ish chunk. A `high`-effort task almost always wants splitting; a `trivial` task is fine if the bar is still met.

### 4. Interview, only if needed

A task is **ready** when it has: verb-led title; 1–3 sentence summary (why + what); `effort`, `impact`, `category` set; a concrete acceptance signal; no unmet blocker dependencies.

If every proposed task can meet the bar from the conversation alone, skip this step. If one or more tasks are missing a required field, ask **bounded, specific questions** — 3–5 maximum, ideally fewer:

- Ask one at a time when the answer to one shapes the next.
- Batch independent questions.
- Favor "what's the acceptance signal for X?" over "tell me more about Y."

If the gaps can't close in 5 questions, the idea isn't ready to file. Say so and ask the user to sit with it a bit longer. Don't file below-bar tasks to escape the conversation.

### 5. Research, only if it pays for itself

If the objective touches territory the conversation didn't resolve — a library the user hasn't used, a domain pattern, a decision point where best-practice isn't obvious — do **targeted web research**. One to three focused searches. Prefer `exa` (`web_search_exa`, `web_fetch_exa`); fall back to `WebSearch` / `WebFetch` only if it isn't available.

Skip research when:

- The idea is entirely internal (refactoring, cleanup, existing patterns).
- The conversation covered the unknowns.
- Research would just confirm what's already known.

Research output goes into task `context`, not into a separate doc. Each task that needed research cites the source inline.

### 6. Wire dependencies, only if natural

- **`blocks`** — hard ordering. B needs A's output to even start.
- **`relates_to`** — soft context. Readers of B benefit from reading A, but B can execute independently.

Don't over-wire. A flat backlog with a shared `group_key` is often better than a chain of five `blocks` edges. If there are no natural edges, leave the set flat.

### 7. Confirm, then write

Present the proposal in compact form:

```
Idea: [one-line restatement]
Group: [group_key, if multi-task]

1. [title] — effort/impact/category
   Summary: [1–3 sentences]
   Acceptance: [one line]

2. ...

Dependencies: (shown only when present)
  2 blocks 1
  3 relates_to 1
```

Ask: "File these?" Accept inline edits — drop a task, adjust effort, tighten a title. Once confirmed, create all tasks in one batch via `create_task`, then wire dependencies in a second batch.

### 8. Close

One line. The user is thinking about the work itself, not the filing:

```
Filed 3 tasks in Tab (group: search-affordances-v1). /work will pick them up.
```

## Output

One or more tasks in the MCP, all above the readiness bar, optionally linked by `group_key` and dependency edges. No documents, no changes to existing tasks, no branches created.

## Principles

- **Scale rigor to what the input needs, not to what the invocation says.** A one-line idea with full context gets a one-task filing. A paragraph about a fuzzy multi-surface goal gets an interview + research + deps. Same skill, same mental model.
- **Interview is a tool, not a phase.** Ask when a specific field is missing; skip when it isn't. Ceremony is the enemy.
- **Decompose along seams the user named.** Inventing splits creates phantom structure; trust what's said.
- **File what's ready, defer what isn't.** A clean filing of one ready task beats a rushed filing of three half-specified ones.
- **Confirm once, then get out of the way.** The user is still thinking about the work; filing is overhead.

## Constraints

- **No writes below confident project inference.** Ask or stop.
- **No writes until confirmed.** The full proposal is shown before any task is created.
- **No codebase search.** Web research and bounded interview only. The user's intent is the source for *what to build*; research informs *how*.
- **Readiness bar is non-negotiable.** Every filed task meets the bar or isn't filed.
- **Don't edit existing tasks.** This skill creates. Grooming is `/backlog`'s job.
- **Interview is bounded.** 3–5 questions maximum. Beyond that, the idea isn't ready.
