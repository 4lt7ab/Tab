---
name: project
description: Session-oriented project planning. Opens on a project (existing or brand-new), scores backlog health against the readiness bar, then hosts an open-ended iteration loop for initiatives, research, decisions, and drive-by filings until the user closes the session. Captures tasks and KB documents as conclusions accumulate, not as a single end-of-session dump. Triggers on `/project` and phrases like "let's work on X", "plan out Y", "start a session on Z", "spin up a new project for W".
argument-hint: "[project hint, initiative, or objective]"
---

The "open a planning session" skill. The user shows up with a project in mind and a session's worth of thinking to unpack — some of it initiatives, some of it research questions, some of it decisions that should become KB docs, some of it grooming drift. This skill opens on the project (resolving or offering to create), scores what's there once, and then hosts the session until the user closes. Replaces `/feature`.

## Trigger

**When to activate:**
- User invokes `/project` optionally followed by a project hint, initiative, or objective inline.
- User says "let's work on <project>", "plan out <initiative>", "start a session on <codebase>", "spin up a new project for <objective>", "time to plan <thing>".
- User is opening a conversation scoped around a project and wants initiatives, research, or decisions captured as they land.

**When NOT to activate:**
- User wants to file a single small task from the conversation — use `/fix`.
- User wants to groom an existing backlog — use `/backlog` (though `/project` will point at `/backlog` when grooming is warranted).
- User wants to execute ready tasks — use `/work`.
- User wants to save a single doc and move on — use `/document`.
- User wants to find an existing doc or task — use `/search`.
- User is still thinking and hasn't committed to any shape or project — use `/think`.

## Requires

- **MCP:** `tab-for-projects` — for project resolution, project creation, task reads/writes, document reads/writes, dependency wiring, `get_project_context` for health evaluation.
- **MCP (preferred):** `exa` — `web_search_exa` and `web_fetch_exa` for technical research. Better signal than native search.
- **Tool (fallback):** `WebSearch` / `WebFetch` — used only when `exa` isn't available.

## Behavior

The session flows in three phases: **Open** (resolve, evaluate, summarize), **Iterate** (loop on the user's shifting modes until close), **Close** (short recap, suggest next step). Don't force the user to re-invoke the skill for each new initiative, research thread, or doc capture — the loop is the point.

### 1. Open — resolve the project

Follow the shared Project Inference convention:

1. Explicit `project:<id or title>` argument wins.
2. Read `.tab-project` at repo root if present.
3. Parse git remote `origin`; exact repo-name match is high confidence.
4. Match cwd basename and parent segments against project titles.
5. Fall back to most recently updated plausible project. Never sole signal.

Three resolution branches:

- **Confident match (existing project)** — state the project in the opening line and proceed to health evaluation.
- **Ambiguous (2+ plausible projects)** — list the top 2–3 and ask which. No writes, no evaluation, no creation prompts until the user picks.
- **No match at all** — offer to create a new project. Never silent-create. Use this prompt shape:

```
No existing project matches. Create a new one?

  Title: <proposed — from cwd basename, git repo name, or the user's invocation>
  Summary: <one line if the invocation carried intent, else blank>

Create? (y / edit / pick existing instead)
```

On `y`, call `create_project` with the confirmed title (+ summary if supplied). The returned `project_id` becomes the session's project. On `edit`, accept inline edits to title/summary and re-confirm. On `pick existing`, fall back to a short `list_projects` with a search term and let the user choose.

**Hard rule:** no MCP writes of any kind below confident resolution. Project creation counts as a write — it gets the same confirmation bar as a task write.

### 2. Open — evaluate backlog health (read-only)

Run once per session, right after resolution, before the loop opens. Goal: surface actionable state in one glance, not produce an audit report.

Primary read: `get_project_context` — token-budgeted and pre-tiered. Fall back to `list_tasks` + `list_documents` only when finer detail is needed for a specific signal.

Signals to extract:

| Signal | What it measures | How it presents |
| --- | --- | --- |
| **Readiness-bar conformance** | % of `todo` tasks that meet the bar (title + summary + effort + impact + category + acceptance signal). | `X/Y tasks ready for /work` |
| **Below-bar count** | Tasks missing one or more bar fields. | `Z below bar` (only shown if Z > 0) |
| **Stale tasks** | `todo` tasks with `updated_at` older than 30 days. | `N stale (untouched 30+ days)` (only shown if N > 0) |
| **Unblocked blockers** | Tasks whose `blocks` edges are all `done`/`archived` but which weren't reconsidered. | `M unblocked — ready to reassess` (only shown if M > 0) |
| **In-progress load** | Tasks currently `in_progress`. | `K in flight` |
| **Doc coverage** | Number of docs linked. If zero and the project has ≥ 5 tasks, surface once. | `No docs linked — consider capturing conventions or decisions` (conditional) |
| **Recent activity** | Last update timestamp at the project level. | `Last activity: 2d ago` |

Do **not** run any writes during evaluation. Do **not** attempt to groom as a side effect — that's `/backlog`'s job; the summary's role is to point at it, not do it.

### 3. Open — present the summary

Single block, scannable, followed by the open-ended prompt:

```
Project: Tab (01KN6H…)
Last activity: 2d ago · 11/14 tasks ready · 3 below bar · 1 unblocked · 5 docs linked

In flight: 2
  01KY… Refactor session store (implementer)
  01KZ… MFA enrollment (architect)

Below bar (3):
  01K1… "Improve search performance" — no acceptance signal
  01K2… "Investigate X" — blocked by 01K3… (also below bar)
  01K3… "Rethink Y" — no summary

Suggest: /backlog to groom the 3 below-bar items before we file new work.

What are we working on?
```

Three rules:

1. **One block, scannable.** Not three paragraphs. The user opened the session to do something, not read a report.
2. **Conditional sections only when non-empty.** Suppress below-bar, stale, unblocked, and doc-coverage rows when the count is zero. No "0 stale" filler.
3. **End with the open-ended prompt.** `What are we working on?` invites the user to raise the first move without prescribing shape.

### 4. Iterate — classify each turn and respond in kind

The loop runs until the user closes. Each turn, classify the user's input into one of these shapes and respond accordingly. Never force the user to re-invoke the skill between shifts.

| Shape | Signals | Response |
| --- | --- | --- |
| **New initiative** | "I want to build", "let's plan", "break down", "file tasks for" | Run the capture sub-flow (§5). |
| **Research question** | "how do teams", "what's the right way", "is there a pattern for", a named technology the user hasn't used | Research sub-flow (§7); fold findings into task context or propose a KB doc. |
| **Decision / convention** | "we decided", "we're going with", "from now on" | KB capture sub-flow (§6). |
| **Single drive-by task** | "add a todo for", "don't let me forget", "file this small thing" | Single-task filing — same shape `/fix` uses. Confirm once, write, loop back. |
| **Grooming request** | "groom", "what's below bar", "clean up tasks" | Hand off to `/backlog`-shaped sub-flow (read the below-bar list, propose fixes or splits, confirm, write). |
| **Status / search** | "what's in flight", "find that doc about X" | Read-only answer (`list_tasks`, `search_documents`, etc.). No sub-flow, no writes. |
| **Ambiguous / still thinking** | Open-ended musing with no commit | Acknowledge; ask one bounded clarifying question, or invite continued thinking. Do not file. |

### 5. Iterate — initiative-capture sub-flow

The most common path. Inherit the shape `/feature` was doing well:

1. Read the invocation plus the surrounding session context. Prior turns in this session count; conversation before the session opened does too.
2. Decide **one task or several** — decompose only along seams the user named. Don't invent splits. If you have to invent the split, it's probably one task.
3. **Interview only if needed** — bounded at 3–5 questions, specific (`"what's the acceptance signal for X?"`), and only to close genuine readiness-bar gaps. If five questions can't close the gaps, say so and suggest the idea sit longer. Don't file below-bar tasks to escape the conversation.
4. **Research only if it pays for itself** — see §7.
5. **Wire dependencies only if natural** — `blocks` for hard ordering, `relates_to` for soft context. A flat backlog with a shared `group_key` is often better than a chain of five `blocks` edges.
6. **Confirm once, then write.** Compact proposal block:

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

Ask: "File these?" Accept inline edits — drop a task, tighten a title, flip effort. On confirm, batch `create_task` calls, then dependency wires. Report the filed IDs and loop back to the open-ended prompt.

**Confirmation cadence:**

- **One confirmation per write batch**, not one per initiative's component tasks. Three tasks for initiative A → one confirm of the batch. Initiative B that follows gets its own single confirmation.
- **No implicit "auto-apply" mode.** Every write — task, doc, or project entity — passes through a visible confirm. The session's value is shared thinking, not batch speed.
- **Inline edits on the confirmation block are always accepted.** The user shouldn't have to cancel and restart to adjust.

### 6. Iterate — KB documentation sub-flow

`/project` is a **client** of `/document`'s shape, not a duplicate. When a decision crystallizes, a convention gets named, or research produces a reusable artifact, invoke the same compact confirm shape inline. Don't make the user exit the session to capture.

**When to propose capture:**

1. **A decision just crystallized.** The conversation resolved a pro/con thread and the user said "we're going with X".
2. **A convention just got named.** "From now on, we do Y."
3. **Research produced a reusable artifact.** A pattern survey, vendor comparison, or architectural sketch that would be discoverable by other tasks later.
4. **The project has zero docs and is ≥ 5 tasks old** — raise once in the opening summary, then let the user direct.

**When NOT to capture:**

- The content is a single task's `context` — that's not a doc, it's task context.
- The user is mid-thought and the decision isn't settled — offer to capture when it is.
- The content is a restatement of an existing KB doc — suggest `update_document` on the existing one instead.

**Capture flow:** propose the doc in the same compact shape `/document` uses (title, folder, tags, summary, first ~15 lines of content, attach-to-project defaulting to yes since the session is project-scoped). On confirm, call `create_document` and `update_project` to link. Loop back.

The user can always hand off to `/document` for a standalone capture ("actually let me `/document` this separately"). Behavior is identical; invocation is different.

### 7. Iterate — research sub-flow

**Primary tool:** `exa` MCP — `web_search_exa` and `web_fetch_exa`.
**Fallback:** `WebSearch` / `WebFetch`.

**When research is worth it:**

- The initiative touches a library, API, or domain pattern the conversation didn't resolve.
- The decision hinges on best practices the user asked about explicitly ("what's the right way to do X").
- The user is planning against a codebase where the target tech is unfamiliar.

**When to skip:**

- The idea is entirely internal — refactor, cleanup, existing patterns.
- The conversation already covered the unknowns.
- Research would just confirm what's already known.
- The user is in a drive-by filing flow.

**Depth:** one to three focused searches per thread. Not a literature review. If the first three don't converge, the question is probably too broad — narrow with the user and retry, or capture it as an open question in the relevant task.

**Research output placement:**

- Into task `context` when the finding informs a specific task. Cite the source URL inline.
- Into a KB doc when the finding has standalone value (pattern survey, vendor comparison). Trigger the capture sub-flow (§6).
- Into the session's running conversation when the finding informs the user's next move but doesn't belong anywhere persistent yet.

Never file raw search-result lists as task context. Synthesize, summarize, cite.

### 8. Iterate — group_key conventions

Two conventions layered on the existing `group_key` field (32-char max).

**One group per initiative.** Every multi-task initiative captured in the session gets its own `group_key`. Single-task drive-bys don't need one. Key shape: short, verb- or noun-led, lowercase with hyphens. `mfa-enrollment`, `search-affordances-v1`, `token-rotation-fix`. The skill proposes a key from the initiative's summary; the user can override.

**Team attribution via prefix** (opt-in). When the session is happening on behalf of a named team:

```
team:<team-name>:<initiative-name>
```

Examples: `team:platform:mfa-enroll`, `team:ui:search-v1`. The `team:` prefix is a convention — the MCP doesn't parse it — but it unlocks downstream discovery (`list_tasks` with `group_key: team:platform:...`, prefix filters in `/search`) without introducing a new MCP primitive.

**The 32-char ceiling.** `team:` is 5 chars. Practical budget: team ≤ 8, initiative ≤ 18, total ≤ 32. Validate at confirm time. If the proposed key exceeds 32 chars, propose a shortened form (`team:platform-infra:mfa-enrollment → team:pinfra:mfa-enroll?`) and ask. **Never silently truncate.**

No team attribution is a valid choice. If the session isn't team-scoped, use just the initiative name (`mfa-enrollment`).

### 9. Close

Triggered by the user saying "that's it", "done for now", "close out", "ship it", or similar. The skill can also recognize a natural end when the user starts a fresh, off-topic turn — confirm closing rather than assuming.

Produce a short recap and a suggestion:

```
Session recap — Tab project

Filed 4 tasks in 2 initiatives:
  - mfa-enrollment: 01KX…, 01KY…, 01KZ… (3 tasks, architect + implementer routing)
  - token-rotation-fix: 01KW… (1 task)

Saved 2 KB docs:
  - 01KQ… "Decision: MFA vendor selection"
  - 01KR… "Conventions: Session token rotation"

Suggest: /work to execute the mfa-enrollment group — all 3 tasks are ready and sit in a natural chain.
```

Keep it short. The user wants to move on.

## Output

- Zero-or-more tasks in the MCP, all above the readiness bar, optionally linked by `group_key` and dependency edges.
- Zero-or-more documents in the MCP, attached to the project when content is project-specific.
- Optionally a new project record (when the session opened against a non-existent project and the user confirmed creation).
- A session recap block at close.

No branches created, no code executed, no existing tasks silently edited.

## Principles

- **Session-first, not invocation-first.** The user doesn't dismount to file each initiative, research each question, or save each doc. One invocation, many turns, many small confirmed writes.
- **Research posture is primary, not opt-in.** If the initiative touches unfamiliar territory and the conversation didn't resolve it, research before filing. When it doesn't, skip cleanly.
- **Confirmation per write batch.** Each initiative's tasks confirm as a set. Each doc confirms separately. Each drive-by confirms standalone. No session-level "auto-apply".
- **Grooming is visible, not silent.** Below-bar tasks show up in the opening summary and get handed off to `/backlog` — never silently auto-filled during health evaluation.
- **The KB accumulates as sessions land.** Decisions that might otherwise have stayed in a conversation get captured at the moment they crystallize.
- **The invocation is the opening line, not the whole brief.** The user rarely arrives with every field resolved; the session shapes the work as it goes.

## Constraints

- **No writes below confident project inference.** Ask, offer creation, or stop.
- **Project creation is never silent.** Always confirmed with title/summary before `create_project` fires.
- **No writes until confirmed.** Tasks, docs, and dependency edges all pass through a visible confirm block.
- **Readiness bar is non-negotiable.** Every filed task meets the bar or isn't filed.
- **Don't groom silently during health evaluation.** Surface the number, suggest `/backlog`, move on.
- **Don't execute code.** `/project` writes tasks and docs. `/work` executes. If the user says "go build X," capture + suggest `/work`.
- **Don't edit existing tasks** during capture. Grooming is `/backlog`'s job; `/project` can hand off.
- **Interview is bounded.** 3–5 questions max per initiative. Beyond that, the idea isn't ready.
- **No codebase search as a substitute for the user's intent.** The user's words are the source for *what to build*; research informs *how*. Ask before spelunking the repo.
- **One session at a time per conversation.** No parallel `/project A` + `/project B` in the same conversation; closing one is implicit before opening another.
- **group_key respects the 32-char ceiling.** Validate at confirm; never truncate silently.
