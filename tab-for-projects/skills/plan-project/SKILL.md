---
name: plan-project
description: Turn a broad objective into a well-groomed backlog of tasks that start above the readiness bar. Interviews the user briefly, researches unknowns on the web when useful, decomposes into PR-sized units, and wires up dependencies. Use when the user wants to stand up a chunk of work across many tasks, not fix a single thing. Triggers on `/plan-project` and phrases like "plan out the work for X", "break this down into tasks", "build me a backlog for Y".
argument-hint: "[objective]"
---

Take a fuzzy objective and produce a backlog the user can hand to `/work` without further grooming. The skill's job is to do the thinking, research, and decomposition work that normally happens in a planning session — compressed into one invocation and written straight to the MCP.

## Trigger

**When to activate:**
- User invokes `/plan-project` with an objective.
- User says "plan out the work for X", "break this down into tasks", "build a backlog for Y", "what would it take to ship Z".
- User wants multiple tasks created at once, across a meaningful scope.

**When NOT to activate:**
- User wants a single task captured from conversation — use `/fix`.
- User wants to execute existing tasks — use `/work`.
- User wants to groom an existing backlog — use `/backlog`.
- User is still thinking out loud and hasn't committed to scope — use `/think`.

## Requires

- **MCP:** `tab-for-projects` — for project resolution, task creation, dependency wiring.
- **MCP (preferred):** `exa` — `web_search_exa` and `web_fetch_exa` for research. Better results than native search for technical topics.
- **Tool (fallback):** `WebSearch` / `WebFetch` — used only when the `exa` MCP is unavailable.

## Behavior

### 1. Resolve the project

Resolve which project this run targets:

1. Explicit `project:<id or title>` argument wins.
2. Read `.tab-project` at repo root if present.
3. Parse git remote `origin`; exact repo-name match against project titles is high confidence.
4. Match cwd basename and parent segments against project titles.
5. Fall back to most recently updated project among plausible candidates. Never sole signal.

If confidence is below **confident**, surface the top 2–3 candidates and ask. Writes are forbidden below confident.

State the resolved project in the opening line so the user can catch a bad inference before any tasks are written.

### 2. Clarify the objective

Conduct a **short interview** — 3–5 focused questions, not a requirements workshop. Aim for:

- **Scope boundary.** What's in, what's out? What's the stopping point?
- **Acceptance.** How will the user know the whole objective is done?
- **Constraints.** Deadlines, technical constraints, decisions already made.
- **Known unknowns.** What does the user *not* know yet that might block planning?

Ask one question at a time when the answer to one shapes the next. Batch independent questions.

### 3. Research, when it pays for itself

If the objective involves unfamiliar territory — a library the user hasn't used, a domain pattern the user wants to learn, a decision point where best-practice isn't obvious — do targeted web research. One to three searches, focused. Prefer `exa` (`web_search_exa`, `web_fetch_exa`) when available; fall back to `WebSearch` / `WebFetch` only if it isn't.

Skip research when:
- The objective is entirely internal (refactoring, cleanup, existing patterns).
- The user's answers in the interview covered the unknowns.
- Research would just confirm what's already known.

Research output goes into task context, not into a separate doc. Each task that needed research cites the source inline.

### 4. Decompose into units of work

Every task produced must start above the readiness bar:

- Verb-led title
- 1–3 sentence summary (why + what)
- `effort`, `impact`, `category` set
- Concrete acceptance signal (test, behavior, artifact produced/removed)
- `status: todo`

Sizing: one task = one PR-ish chunk. If a task feels like two things in a trenchcoat, split it. If a task is `trivial` effort, fine — but it still gets the full bar.

Use `group_key` to tie related tasks together. One objective usually maps to one `group_key`.

### 5. Wire up dependencies

- **`blocks`** — hard ordering. B needs A's output to even start.
- **`relates_to`** — soft context. Readers of B benefit from reading A, but B can execute independently.

Don't over-wire. A flat backlog with a `group_key` is often better than a chain of five `blocks` edges.

### 6. Confirm, then write

Present the proposed backlog to the user as a table or list:

```
Objective: [one line]
Group: [group_key]

1. [title] — effort/impact/category — [one-line acceptance signal]
2. [title] — ...
...

Dependencies:
  2 blocks 1
  3 relates_to 1
```

Ask: "Write these?" Accept edits before writing. Once confirmed, create all tasks in one batch, then wire dependencies in a second batch.

## Output

A set of tasks in the MCP, all above the readiness bar, with dependencies wired. Skill closes with a short summary:

```
Created 7 tasks in Tab (group: auth-v2).
4 ready to execute, 3 blocked on task 01KX… (expected — that's the ordering).
/work will pick these up.
```

## Principles

- **Interview, don't interrogate.** 3–5 questions. If you want more, write them as tasks and ask them in the executing work, not in the planning session.
- **Decomposition is the product.** The value isn't the questions or the research — it's turning one fuzzy goal into N concrete tasks that a subagent can execute cold.
- **Bias to more, smaller tasks.** A `high`-effort task almost always wants splitting. `/work` batches well; `/work` doesn't split well.
- **Don't plan past the edge of confidence.** If the objective has real unknowns past task 3, stop at task 3 and note "task 4+ depends on outcome of 3." Don't fabricate a plan you don't believe.

## Constraints

- **No writes until confirmed.** The whole backlog is proposed before any task is created.
- **No writes below confident project inference.** Ask or stop.
- **Readiness bar is non-negotiable.** A task that can't meet the bar from this session's context isn't written — it's surfaced to the user as a gap.
- **Don't archive or modify existing tasks.** This skill creates. Grooming is `/backlog`'s job.
