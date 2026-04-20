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
- **No match at all** — offer to create a new project. Never silent-create. The full creation dialog (initial proposal, iterative edit loop with re-confirmation, 5-edit cap with `keep going` override, post-create acknowledgement, and the `pick existing instead` fallback) is locked in addendum doc `01KPMAFVJ6CDQMGMJRMYDKECAR` (`Design: /project creation prompt and edit-loop mechanics`). Quote the blocks below verbatim; refer to the addendum for rationale and alternatives considered.

**(a) Initial proposal block (addendum §3.1).** Present once per session entry into the no-match branch:

```
No existing project matches. Create a new one?

  Title: <proposed>
  Summary: <one line if the invocation carried intent, else (none)>

Create? (y / edit / pick existing instead)
```

Proposal sources, in priority order:

1. **Title** — the user's invocation when it carried a clear noun phrase (`spin up a new project for the auth-rewrite` → `auth-rewrite`); else git remote `origin` repo name; else cwd basename. Strip leading `the`, trailing punctuation, and obvious connector words. Title-case.
2. **Summary** — one line synthesized from the invocation when intent is present. Otherwise the literal token `(none)` is shown to make the empty state explicit; the field is left empty in the eventual `create_project` call.

**(b) Iterative edit prompt + field prompts (addendum §3.2).** On `edit`, ask which field with the current proposal restated:

```
Which field?

  1. Title:    <current proposed title>
  2. Summary:  <current proposed summary, or (none)>

(1 / 2 / both / cancel)
```

- `1` — prompt for a new title only.
- `2` — prompt for a new summary only.
- `both` — prompt for title, then summary, in sequence.
- `cancel` — drop the edit, return to the initial proposal block (a) unchanged.

Field prompts are minimal:

```
New title:
```

```
New summary (or (none) to clear):
```

The `(none)` sentinel lets the user explicitly clear an existing summary back to empty.

**(c) Re-confirmation block with `(changed)` markers (addendum §3.3).** After every accepted edit, re-present the full proposal with `(changed)` on fields that moved this round:

```
Updated proposal:

  Title: <updated>     (changed)
  Summary: <updated>   (changed)

Create? (y / edit / pick existing instead)
```

The `(changed)` marker only appears on fields that moved this round. If neither field changed (e.g., the user typed a new title identical to the current one), omit the marker and prepend `No changes — same proposal as before.` above the block.

**(d) 5-edit cap with `keep going` override (addendum §3.4).** When the user accepts a 6th edit, surface the cap once before continuing:

```
This is the 6th revision. Two options if the proposal still isn't landing:

  - `pick existing` — search for an existing project instead of creating a new one.
  - `cancel` — drop the proposal and re-invoke /project with a clearer hint.

Or keep editing — say `keep going` and we'll continue.
```

If the user says `keep going`, the cap is suppressed for the rest of this proposal — do **not** re-surface it.

**(e) Post-create acknowledgement (addendum §3.5).** On `y`, fire `create_project` with the confirmed title and summary (omitting the summary field entirely when it's `(none)`). Acknowledge the new ID and segue into the open-ended prompt — no health evaluation runs (there's nothing to evaluate):

```
Created: <Title> (<project_id>)

New project — no backlog yet, no docs yet.

What are we working on?
```

**(f) `pick existing instead` selection UI (addendum §4).** On `pick existing instead`, build the search term from the same signals that fed the title proposal (invocation noun phrase → git remote → cwd basename; first non-empty wins). Call `list_projects` with that title-search filter, capped at **8 results**, ordered `updated_at` desc. Present:

```
Looking for an existing project matching `<search term>`:

  1. <Title> (<id-prefix…>) — last activity <relative-time>
  2. <Title> (<id-prefix…>) — last activity <relative-time>
  ...

(Number to pick / `search <term>` to retry / `back` to return to the create proposal / `cancel` to abort the session)
```

Four responses:

- **Number** — confirm the choice in one line (`Using: <Title> (<id>)`) and proceed to health evaluation as if inference had landed on this project.
- **`search <term>`** — re-run `list_projects` with a new term. Same cap (8), same ordering, same UI. **No iteration cap on searching** — the user is searching, not editing a write proposal.
- **`back`** — return to the initial creation proposal (a) unchanged.
- **`cancel`** — close the session without creating or selecting. Acknowledge with `No project selected. Re-invoke /project when ready.` and stop.

When `list_projects` returns zero matches, **do not auto-fall-back to the create proposal**:

```
No existing projects match `<search term>`.

(`search <term>` to retry / `back` to the create proposal / `cancel` to abort)
```

When exactly one result matches, still present the selection UI — **do not auto-select**. The numeric pick is the explicit confirmation.

**(g) Re-confirmation cadence summary (addendum §5).** For implementer reference:

| Event | Cadence |
| --- | --- |
| Initial proposal | One block, awaits `y` / `edit` / `pick existing instead`. |
| Each accepted edit | Re-present the full updated proposal block with `(changed)` markers; awaits explicit `y` again. |
| 5-edit cap reached | Surface the cap prompt once; user picks among `pick existing` / `cancel` / `keep going`. |
| `pick existing` selection | One-line `Using: <Title>` confirmation; no separate "is this right?" prompt — the explicit numeric pick is the confirmation. |
| `pick existing` re-search | Re-present results UI; no additional confirmation between searches. |
| `y` on a proposal | One-line `Created: <Title> (<id>)` acknowledgement; transition to the new-project prompt (no health evaluation, since there's nothing to evaluate). |

Underneath: **every state change that produces a write fires through an explicit affirmation; every state change that's read-only or navigational does not.**

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

The full close flow — trigger, confirm, recap, no-persistence — is locked in addendum doc `01KPMASNH26NVDP038ZZ1ZDA50` (`Design: /project session-close UX`). Quote the blocks below verbatim; refer to the addendum for rationale, alternatives considered, and the worked-example variants.

**Trigger surface (addendum §2).** The close trigger is a **detected closing-phrase list** that prompts a single confirmation before the recap renders. There is **no `/close` slash command**, **no idle/silence heuristic**, and **no auto-close on fresh-topic detection** — fresh-topic detection only escalates to the same confirm prompt.

**(a) Closing-phrase list (addendum §2.5, locked).** Match case-insensitive, with light tolerance for punctuation/leading whitespace. The match must be **the substantive content of the user's turn** — a phrase embedded inside a longer initiative ("that's it for the auth piece, now let's plan billing") doesn't trigger.

| Phrase | Notes |
| --- | --- |
| `that's it` / `that is it` | Most common natural close. |
| `done for now` | Common natural close. |
| `close out` / `let's close out` | Direct close intent. |
| `wrap up` / `let's wrap up` / `wrap it up` | Common. |
| `ship it` | Sometimes ambiguous; see (b) disambiguation. |
| `i'm good` / `we're good` / `we're done` / `i'm done` | Natural close. |
| `that's all` / `that's all for now` / `that's all i've got` | Natural close. |
| `let's stop here` / `stop here` / `we can stop here` | Direct close. |
| `end session` / `close session` / `end the session` | Explicit close. |
| `/close` (typed inline as text, not a slash command) | Treated as an explicit close phrase even though `/close` isn't a registered skill. |

**Fresh-topic detection** is a separate signal, not a phrase. It escalates to the same confirm prompt when **all three** of these hold:

1. The user's turn names a project, codebase, or domain that doesn't match the active session's project.
2. The turn carries an intent verb (`let's plan`, `start a session`, `work on`) — not a passing reference.
3. The turn doesn't contain any closing phrase (otherwise the phrase wins and there's nothing to escalate).

If the user replies `not yet` to the escalated confirm, the new topic is absorbed into the loop normally.

**(b) `ship it` disambiguation (addendum §2.6).** `ship it` is the only listed phrase with realistic in-session ambiguity — it can mean "close the session" or "file the tasks I just confirmed". Resolve as follows:

- If the **previous skill turn** was a write-confirmation prompt (`File these?`, `Create document?`, `Create the project?`), `ship it` resolves to **affirm the write**, not close. The skill treats it as a `y` for the pending confirm.
- Otherwise, `ship it` resolves to a **close trigger** and routes through the standard close confirm.

State the interpretation in one line so the user can correct:

```
Reading 'ship it' as confirming the write above. Filing now.
```

or

```
Reading 'ship it' as closing the session. Recap below — confirm to close.
```

**(c) Close-confirm prompt (addendum §2.7, locked copy).** On any close trigger (phrase match or fresh-topic escalation):

```
Closing the session?

  (y / not yet)
```

Two responses, no third option:

- **`y`** — render the recap (below) and end the session.
- **`not yet`** — return to the loop without rendering the recap. Acknowledge with `Continuing — what's next?` and wait for the next turn.

**Recap block (addendum §3).** One scan-shaped block, ordered by entity type, with task IDs and doc IDs surfaced for downstream reference. The recap fires once after `y`; no follow-up prompts.

**(d) Recap structure (addendum §3.1, locked template).**

```
Session recap — <Project Title> (<project-id-prefix…>)

Filed <N> task<s> in <M> initiative<s>:
  - <group_key_1>: <id1>, <id2>, <id3> (<count> tasks, <category-routing-note>)
  - <group_key_2>: <id4> (<count> task)
  - (no group): <id5> (<count> drive-by task)

Saved <P> KB doc<s>:
  - <doc_id_1> "<Doc Title>" — <folder>
  - <doc_id_2> "<Doc Title>" — <folder>

Created project: <Project Title> (<project-id>)   ← only when the session created the project

No writes this session.   ← shown instead of the above when nothing landed

Suggest: <one-line next step — see (g) below>
```

**(e) Inclusion rules (addendum §3.2).**

- **Tasks:** every `create_task` that fired during the session, grouped by `group_key`. Drive-bys (no `group_key`) collapse into a single `(no group)` line. Updates to existing tasks are not included — only newly-filed tasks.
- **Documents:** every `create_document` that fired during the session. Updates to existing docs collapse into a single `Updated <Q> existing doc<s>: <id> "<Title>"` line below the saved-docs block.
- **Project creation:** if the session created the project, surface it as a separate line below the docs block. If the project was resolved via inference, suppress this line entirely.
- **Dependencies wired:** suppressed from the recap by default. The IDs are enough for follow-up inspection via `/search` or `get_task`.

**(f) Ordering (addendum §3.3).**

- **Initiatives:** in the order they were filed during the session (chronological).
- **Tasks within an initiative:** in the order they were created (chronological within the batch).
- **Docs:** chronological.

**(g) `Suggest:` line priority (addendum §3.4).** One short suggestion, picked from this priority order:

1. **`/work` is ready and natural** — at least one filed initiative has all tasks above the bar with no `blocks` edges to non-`done` tasks outside the group. Suggest: `/work to execute the <group_key> group — all <N> tasks are ready.`
2. **`/backlog` is needed** — the opening summary flagged below-bar tasks that weren't groomed during the session. Suggest: `/backlog to clear the <Z> below-bar items before kicking off /work.`
3. **Open question worth a follow-up session** — the session captured an open thread that wasn't filed. Suggest: `Worth a follow-up /project session on <topic> when ready.`
4. **No clear next step** — suggest nothing. Drop the line entirely rather than padding with a generic "good session".

Suggestions are advisory. The skill never auto-invokes another skill from the recap.

**(h) Routing-note derivation (addendum §3.5).** The parenthetical category note on each initiative line summarizes which subagents `/work` would route the group's tasks to:

| Tasks in the group | Routing note |
| --- | --- |
| All `feature` / `bugfix` / `refactor` / `perf` / `infra` / `chore` | `implementer routing` |
| All `design` | `architect routing` |
| All `test` | `test-writer routing` |
| All `docs` | `docs-writer routing` |
| All `security` | `implementer routing` (no security-specialist agent exists) |
| Mixed categories | List the agents that would be touched, comma-separated, in the order they'd be hit by a topological walk: `architect + implementer routing`, `implementer + docs-writer routing`, etc. |
| Single drive-by task | Omit the routing note; the `(no group)` line is short enough without it. |

This is informational — `/work` does the actual routing.

**(i) Worked example (addendum §3.6).** A two-initiative session with a drive-by, two docs, and a project created from scratch:

```
Session recap — Auth Rewrite (01KQ8X…)

Filed 5 tasks in 3 initiatives:
  - mfa-enrollment: 01KX1A…, 01KY2B…, 01KZ3C… (3 tasks, architect + implementer routing)
  - token-rotation-fix: 01KW4D… (1 task, implementer routing)
  - (no group): 01KV5E… (1 drive-by task)

Saved 2 KB docs:
  - 01KQ7F… "Decision: MFA vendor selection" — decisions
  - 01KR8G… "Conventions: Session token rotation" — conventions

Created project: Auth Rewrite (01KQ8X…)

Suggest: /work to execute the mfa-enrollment group — all 3 tasks are ready.
```

A session with no writes:

```
Session recap — Tab (01KN6H…)

No writes this session.

Suggest: /backlog to clear the 3 below-bar items before kicking off /work.
```

**(j) No MCP persistence (addendum §4).** The recap stays **conversation-local**. The skill does not file a session-summary document, does not append to a project-attached log, and does not write any kind of `session` entity to the MCP. Every persistent artifact from the session is a discrete task or document the user already confirmed during the loop.

If the user explicitly says during close `save this recap as a doc`, route to `/document` with the recap content pre-populated. That's a one-off opt-in, not a default behavior. The locked default is no persistence.

**(k) Re-confirmation cadence summary (addendum §5).** For implementer reference:

| Event | Cadence |
| --- | --- |
| Closing-phrase match | Single confirm prompt (c); awaits `y` / `not yet`. |
| Fresh-topic detection (escalation) | Same single confirm prompt; awaits `y` / `not yet`. If `not yet`, the new topic is absorbed into the loop normally. |
| `ship it` near a write-confirm | Resolves to write-affirmation, not close. Skill states the interpretation in one line (b). |
| `ship it` outside a write-confirm | Resolves to close trigger; routes through the standard close confirm. |
| `y` on close confirm | Render recap (d) and end the session. No further prompts. |
| `not yet` on close confirm | Acknowledge with `Continuing — what's next?` and return to the loop. |
| Recap rendered | One-shot output. No follow-up prompt — the suggestion line is advisory only. |

Underneath: **close is one confirm, then a non-interactive recap, then nothing.** No multi-step close ceremony, no post-recap prompts.

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
- **Close is one confirm, then a non-interactive recap, then nothing.** No multi-step close ceremony, no post-recap prompts, no idle/silence auto-close, no auto-close on fresh-topic detection (escalates to the same confirm instead). The recap is conversation-local — no MCP persistence of the session record.
