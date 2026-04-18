---
name: feature
description: Capture a new feature idea as one or more tasks on the project backlog. Reads context from the conversation — no codebase search, no web research, no interview — shapes it into tasks that start above the readiness bar, confirms, and writes. Triggers on `/feature` and phrases like "file this as a feature", "add a feature task for", "put this on the backlog as a feature".
argument-hint: "[idea]"
---

The "I have an idea, write it down" skill. Sibling of `/fix`: `/fix` captures a small leftover, `/feature` captures a new idea. The user provides as much context as they want in the invocation or the surrounding conversation; this skill shapes it into one or more tasks that an autonomous executor could pick up cold.

## Trigger

**When to activate:**
- User invokes `/feature` optionally followed by the idea inline.
- User says "file this as a feature", "add a feature task for", "put this on the backlog as a feature", "capture this idea".
- User has been describing a feature idea in conversation and wants it landed without a planning session.

**When NOT to activate:**
- User wants to file a bug or small drive-by work — use `/fix`.
- User has a fuzzy multi-task objective that needs interview + research + decomposition — use `/plan-project`.
- User is still thinking through the idea and hasn't committed to shape — use `/think`.
- User wants to execute existing tasks — use `/work`.

## Requires

- **MCP:** `tab-for-projects` — for project resolution and task creation.

## Behavior

### 1. Resolve the project

Follow the shared Project Inference convention:

1. Explicit `project:<id or title>` argument wins.
2. Read `.tab-project` at repo root if present.
3. Parse git remote `origin`; exact repo-name match is high confidence.
4. Match cwd basename and parent segments against project titles.
5. Fall back to most recently updated plausible project. Never sole signal.

Below **confident**, ask or stop. No writes below confident.

### 2. Shape the idea into tasks

Read the invocation argument and the surrounding conversation. Do not search the codebase. Do not search the web. The user's words are the source.

Decide whether the idea is one task or several:

- **One task** when the idea is a single coherent change that a single commit (or a single PR) could deliver.
- **Several tasks** when the idea naturally decomposes along seams the user already named — separate surfaces, separate milestones, separate concerns. If you have to invent the split, it's one task.

For each task, fill every field required by the readiness bar:

- **Title** — verb-led, specific. "Add keyboard shortcut for search focus" beats "search shortcut".
- **Summary** — 1–3 sentences, why + what. Pulled from what the user said; don't invent motivation.
- **Acceptance signal** — a concrete test, observable behavior, or artifact. "A new keybinding `Cmd+K` focuses the search input, visible in the keybinding help panel."
- **Effort** — `trivial` / `low` / `medium` / `high` / `extreme`.
- **Impact** — same scale.
- **Category** — `feature` is the default; use `refactor`, `test`, `docs`, etc. only when the task is genuinely that shape.
- **`group_key`** — set when the idea decomposes into multiple tasks so they travel together. Skip for single-task filings.

### 3. Ask at most one question

If exactly one required field can't be inferred confidently, ask **one specific question**. Common gap: the acceptance signal for an idea described abstractly.

If two or more fields are ambiguous across the proposed task set, the idea isn't ready to file as-is. Say so and suggest `/plan-project` for a real planning pass. Don't file below-bar tasks to avoid the conversation.

### 4. Confirm, then write

Present the proposed task (or tasks) in compact form:

```
Idea: [one-line restatement]
Group: [group_key, if multi-task]

1. [title] — effort/impact/category
   Summary: [1–3 sentences]
   Acceptance: [one line]

2. ...
```

Ask: "File these?" Accept inline edits — drop a task, adjust effort, tighten a title. Once confirmed, create the tasks in one batch via `create_task`.

### 5. Close

One line. The user is still thinking about the idea itself, not the filing.

```
Filed 3 tasks in Tab (group: search-affordances-v1). /work will pick them up.
```

## Output

One or more tasks in the MCP, all above the readiness bar, optionally linked by `group_key`. No documents, no changes to existing tasks, no branches created.

## Principles

- **The user's words are the source.** No codebase search, no web search. If the conversation doesn't contain something, ask or defer — don't go find it.
- **File what's ready, defer what isn't.** A clean filing of one ready task beats a rushed filing of three half-specified ones. Below-bar work belongs in `/plan-project`.
- **Confirm once, then get out of the way.** The user is still thinking about the idea; don't turn filing into a review.
- **Decompose along seams the user named.** Inventing splits creates phantom structure; trust what's said.

## Constraints

- **No writes below confident project inference.** Ask or stop.
- **No codebase search, no web research.** This is a capture skill, not a research skill.
- **Readiness bar is non-negotiable.** Every filed task meets the bar or isn't filed.
- **Don't edit existing tasks.** This skill creates. Grooming is `/backlog`'s job.
- **No interview.** One clarifying question is the maximum; beyond that, hand off to `/plan-project`.
