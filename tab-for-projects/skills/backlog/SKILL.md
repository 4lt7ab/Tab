---
name: backlog
description: Groom the project backlog so every task starts above the readiness bar. Fills missing summaries/effort/impact/category/acceptance-signal, splits oversized tasks, wires dependencies, and flags or archives stale work. Use when the backlog has accumulated under-specified tasks, when `/work` reports too many flagged items, or when planning a grooming pass before handing work to agents. Triggers on `/backlog` and phrases like "groom the backlog", "clean up tasks", "get the backlog ready for execution".
argument-hint: "[optional filter: group_key or category]"
---

Take the current backlog of `todo` tasks and move each one to one of four states: **ready** (above the readiness bar), **split** (broken into ready children), **flagged** (specific question surfaced to the user), or **archived** (stale / duplicate / obsolete). The skill does the thinking and the MCP writes, so `/work` can pick up the result without further grooming.

## Trigger

**When to activate:**
- User invokes `/backlog`, optionally scoped to a `group_key` or `category`.
- User says "groom the backlog", "clean up tasks", "get tasks ready for execution", "score the backlog".
- `/work` just ran and reported several flagged tasks — the user wants to close the gaps.

**When NOT to activate:**
- User wants to create new tasks — use `/plan-project` or `/fix`.
- User wants to execute — use `/work`.
- Backlog is already clean — check first; don't run for ceremony.

## Requires

- **MCP:** `tab-for-projects` — for project resolution, task reads/writes, dependency wiring.

## Behavior

### 1. Resolve the project

Resolve which project this run targets:

1. Explicit `project:<id or title>` argument wins.
2. Read `.tab-project` at repo root if present.
3. Parse git remote `origin`; exact repo-name match is high confidence.
4. Match cwd basename and parent segments against project titles.
5. Fall back to most recently updated plausible project. Never sole signal.

Below **confident**, ask. No writes below confident.

### 2. Pull the backlog

`list_tasks` with `status: ["todo"]` and `project_id: <resolved>`. Apply argument filters (`group_key`, `category`) if given. Also pull the dependency graph — a task's readiness depends on its blockers' states.

If the backlog is already clean (all tasks above the bar, no unwired dependencies, no obvious splits), report that and stop. Don't create ceremony.

### 3. Classify each task

For every `todo` task, decide which bucket it falls into. A task is **ready** when all of the following hold: verb-led title; 1–3 sentence summary covering why + what; `effort`, `impact`, and `category` all set; a concrete acceptance signal (a test that must pass, an observable behavior change, an artifact produced, or an artifact removed); no unmet blocker dependencies. Anything missing means the task is below the bar.

The buckets:

- **Ready** — passes the bar. No action needed. Skip.
- **Fixable from context** — one or more required fields missing, but the project context / task title / linked docs make the answer obvious. Propose the fill.
- **Needs user input** — a required field is genuinely ambiguous. Most common: no acceptance signal. Surface with a *specific* question, not a generic "this needs work."
- **Should be split** — the task description implies two or more distinct units of work. Propose the split: child task titles, summaries, shared `group_key`.
- **Should be archived** — stale, duplicate, obsolete, or superseded by other work. Propose archival with a one-line reason.

Also scan for **missing dependencies**: tasks whose summaries reference another task's output but have no `blocks` edge wired. Propose the edge.

### 4. Batch the proposals

Present the full grooming plan before writing. Group by bucket so the user can skim:

```
Backlog groom — Tab project (14 todo tasks)

FIXABLE FROM CONTEXT (6)
  01KX… "Update README badges" → propose: effort=trivial, impact=low, category=docs, acceptance="badges link to correct CI run"
  ...

NEEDS USER INPUT (3)
  01KY… "Improve search performance" → question: what's the acceptance signal — a latency target, or something else?
  ...

SPLIT (1)
  01KZ… "Rewrite auth and add MFA" → propose split into:
    - "Rewrite auth session handling"
    - "Add MFA enrollment flow"
    - "Add MFA verification on login"
    (shared group_key: auth-mfa)

ARCHIVE (2)
  01K1… "Investigate X" → reason: decision already made in 01KPCW… doc
  ...

MISSING DEPENDENCIES (1)
  01K2… blocks 01K3… (child task references parent's output)
```

Ask: "Apply? (y / edit / skip bucket)". Accept batch-level edits before writing.

### 5. Write

Once confirmed, execute the approved changes in batches:

1. Fixable updates → `update_task` batch.
2. Splits → create child tasks, archive parent (or convert parent to tracking shell — user choice once, applied to all splits in the pass).
3. Archives → `update_task` with `status: archived`.
4. Dependency wires → dependency-edge writes.

**Needs user input** tasks are never auto-written. They're handed back as a short list the user can walk through one by one, or defer.

## Output

After writing:

```
Groomed Tab: 6 fixed, 1 split into 3, 2 archived, 1 dependency wired.
3 tasks still flagged for your input (see list above).
Backlog readiness: 11/14 ready for /work.
```

## Principles

- **Raise tasks to the bar. Never lower the bar to clear tasks.** Silently marking underspecified tasks as "ready" corrupts the contract `/work` depends on.
- **Specificity is the product.** "This task is underspecified" is noise. "This task has no acceptance signal — propose one" is value.
- **Splits cost less than merged ambiguity.** When in doubt between one vague task and two clear ones, propose the split.
- **Archive aggressively, write conservatively.** Stale tasks rot the signal. Removing them is cheap.

## Constraints

- **No writes below confident project inference.** Ask or stop.
- **No silent writes.** Every change is shown in the groom plan and confirmed before execution.
- **No auto-fill for genuinely ambiguous fields.** If the skill has to guess the acceptance signal, it asks instead.
- **Don't modify `in_progress` tasks.** Someone's working on those. Skip.
- **Don't execute tasks.** Grooming produces a ready backlog; running it is `/work`'s job.
