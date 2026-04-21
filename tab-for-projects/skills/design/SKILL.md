---
name: design
description: Conversational KB doc capture for a design-category task. Loads the task + linked docs, optionally fires the archaeologist for a research brief on large codebases, then hosts the conversation with the user to produce a decision/architecture/convention document. Writes via `create_document`, links to the project, and optionally marks the originating task done on confirm. Triggers on `/design` and phrases like "let's design X", "work through this design task", "open the design conversation for 01K…".
argument-hint: "<design-task-id> [--no-brief | --brief]"
---

The "design is a conversation, not an autopilot" skill. Design-category tasks don't get executed by `/work` — they get executed by a human at the keyboard, because design decisions encode trade-offs, priorities, and unstated constraints that only the user can supply. This skill hosts that conversation: pulls the task and any context it references, optionally spends an archaeologist pass to survey the terrain before the user burns their own tokens on it, and produces a KB doc that captures the decision at the moment it crystallizes.

See `01KPQ2AA503SNHRZYQHMD6RCPG` — *Design: Design work is user-driven, not autonomous* — for the decision that shaped this skill.

## Trigger

**When to activate:**
- User invokes `/design <task-id>`.
- User says "let's design X", "work through the design task on Y", "open the design conversation for 01K…", "time to decide Z".
- `/work`'s end-of-run report surfaced a design-category task in the "awaiting human" section and the user wants to resolve it.

**When NOT to activate:**
- User wants to file a new design task — use `/fix` or `/project`.
- User wants to execute an implementation task — use `/work`.
- User wants to capture a decision that *already crystallized* in a conversation unrelated to a filed task — use `/document` directly.
- The dispatched task isn't design-category — point the user at the right entry point (`/work` for most categories) rather than repurposing `/design`.

## Requires

- **MCP:** `tab-for-projects` — for `get_task`, `get_document`, `get_project`, `list_documents`, `create_document`, `update_project`, `update_task`.
- **Subagent (optional):** `tab-for-projects:archaeologist` — research briefer. The skill degrades gracefully when the agent isn't available or the user opts out with `--no-brief`.
- **Tools:** `Read`, `Grep`, `Glob` — when a brief isn't run and the conversation needs a quick on-the-fly lookup in the repo. Codebase surveys of any depth belong in the archaeologist, not here.

## Behavior

The skill flows in four phases: **Load** (pull task + linked docs, resolve project), **Brief** (optionally dispatch the archaeologist), **Converse** (host the design decision with the user), **Capture** (propose the doc, confirm, write, link, optionally close the task). Every write passes through an explicit confirmation block.

### 1. Load — pull the task and validate

1. `get_task(task_id)`. If the task doesn't exist, report and stop.
2. **Readiness check.** A design task is ready when its title is verb-led and concrete, its summary explains the *why* and the *what* in 1–3 sentences, and its `acceptance_criteria` names a concrete output (usually: "a KB doc at folder X capturing decision Y"). If any field is missing, surface the gap and ask the user to groom the task via `/backlog` or supply the missing field inline before the conversation opens. No conversation starts on a below-bar task.
3. **Category check.** If the task's `category` isn't `design`, surface that and stop. `/design` is scoped to design-category work. Other categories have their own routes (`/work` for most; `/document` for standalone decisions without a filed task).
4. **Status check.** If the task is already `in_progress`, assume the user is resuming — continue. If the task is `done` or `archived`, report and ask whether the user wants to revisit (which would mean opening a *new* design task rather than reopening this one).
5. `get_document` on every ULID referenced in the task's `context` or `summary`. Read each one — these are the constraints the decision has to respect.
6. Resolve the project. Priority order:
   1. The task's `project_id` (always present — task-scoped skills inherit the task's project).
   2. Sanity-check against the shared inference signals (`.tab-project`, git remote, cwd) only if the task's `project_id` points at a project that looks unrelated to the cwd. If there's a mismatch, surface it and ask before writing.

### 2. Brief — optionally dispatch the archaeologist

The archaeologist is a research subagent (see `tab-for-projects:archaeologist`) that reads the task, linked docs, prior KB decisions, and the relevant source code, then returns a distilled ~1-page brief. It does not make the decision — the brief is raw material for the user.

**When to fire the brief (default heuristic, pending follow-up):** run the archaeologist when the task touches a non-trivial slice of the codebase and the conversation would otherwise burn main-thread context on a survey. Concrete tells:

- The task's summary or context names files, modules, or areas of the codebase the main thread hasn't loaded.
- Prior KB decisions in folders like `architecture`, `decisions`, or `conventions` are plausibly relevant and haven't been listed on the task.
- The user explicitly requests a brief (`--brief`).

**When to skip:** `--no-brief` passed; the task is self-contained (greenfield, no prior code or KB material); the conversation already has the context loaded; the archaeologist subagent isn't available.

The exact trigger heuristic is intentionally soft — tuning it is tracked as a follow-up under the `archaeologist-v1` group (the skill doesn't auto-decide when the signals are weak; it asks).

**If firing:**

1. State the intent in one line: `Running archaeologist for a one-page brief on <task-id>. Hold tight — this is a single dispatch, not a loop.`
2. Dispatch the `archaeologist` subagent with `{ task_id }` only. The agent fetches its own context and returns a structured report (see the agent's outcomes block for shape).
3. On return, render the brief inline for the user to read. If the agent flagged the task back to `todo` (below-bar or non-design), surface the flag, stop the skill, and suggest `/backlog` or re-filing.
4. If the archaeologist filed follow-up design tasks or surfaced open forks the user should decide first, name them before moving on — the user may want to re-scope the current task before the conversation starts.

**If skipping:** state the choice in one line (`Skipping archaeologist — <reason>. Going straight to the conversation.`) so the user can override.

### 3. Converse — host the design decision

This is the skill's core and the reason it exists. The conversation shape mirrors `/think` and the design-capture sub-flow inside `/project`: the user drives, the skill listens, asks, and synthesizes. There's no fixed interview script — design decisions vary too much.

A few rules of thumb for the conversation:

- **Start from the task's question, not a blank page.** Quote the task's summary back. If the archaeologist ran, surface the open forks it named. The opening turn should make the decision visible, not re-elicit it.
- **Surface constraints before options.** Prior KB decisions (from linked docs and any the archaeologist dug up), conventions, and hard code facts come first. The user shouldn't have to discover that an option is already ruled out halfway through weighing it.
- **Name the options explicitly.** Whether they come from the task, the archaeologist's brief, or the user's own head, list the candidate shapes before arguing between them. A decision without named alternatives is a decision without evidence.
- **Push back on hand-waves.** "We'll figure that out later" is a fork, not an answer. If the user punts on a fork, offer to file it as a follow-up design task and keep going on what's decidable now.
- **Stay out of the user's taste calls.** When the user has a preference grounded in priorities the skill can't see, the skill's job is to capture it cleanly, not to litigate it.
- **Depth scales with stakes.** A small convention call lands in a short exchange; an architectural decision that constrains months of work earns a longer conversation. Don't artificially inflate the low-stakes cases.

The conversation closes when the user signals the decision is made — explicit phrases (`okay, let's go with X`, `decision's made`, `capture that`), or a natural landing where the last N turns restated the same conclusion without new information.

### 4. Capture — propose the doc, confirm, write

Once the decision is in hand, synthesize the KB doc. Follow the same shape `/document` uses — this skill is a client of that shape, not a duplicate.

**Decide the doc type.** Three shapes fit most design conversations:

- **Decision** — a single resolved trade-off. Folder: `decisions` (or `architecture` if architectural). Tags: `decision`, plus domain if obvious (`architecture`, `data`, `integration`, `security`, `ui`, etc.).
- **Architecture** — a shape that multiple decisions or features will reference. Folder: `architecture`. Tags: `architecture`, `reference`.
- **Convention** — a rule the project will apply consistently from here on. Folder: `conventions`. Tags: `conventions`, `reference`.

Generic rule: **match what's already there.** Before proposing a folder or tag, `list_documents(project_id)` to see what the project uses. Introduce new folders sparingly.

**Build the doc:**

- **Title** — follow the KB patterns: `Decision: <short phrase>`, `Architecture: <short phrase>`, `Conventions: <short phrase>`. Pick the pattern that matches the type.
- **Summary** — 1–3 sentences, max 500 chars. What the doc locks down and who it's for. This is load-bearing — `/search` finds docs by this summary.
- **Content** — structured markdown. A typical decision doc has sections: **Decision** (the resolved answer in 2–4 sentences), **Why** (the reasoning and the alternatives considered), **Consequences** (what this locks in, what it doesn't, known follow-ups), **Related** (linked tasks, sibling docs, group keys). Architecture and convention docs vary in shape — match what neighboring docs in the same folder look like.
- **Folder / Tags** — from the type classification above.

**Propose before writing:**

```
Save as: "Decision: <short phrase>"
  Folder: decisions
  Tags: decision, architecture
  Attach to: <Project Title> (<project-id-prefix…>)
  Close task: 01K…  (optional — "y" here marks the originating design task done)
  Summary: [1–3 sentences]

Content preview (first ~20 lines):
  [render first chunk]

Save? (y / edit / skip attach / skip task-close)
```

Accept inline edits on title, folder, tags, summary, content. `skip attach` keeps the doc unlinked from the project (rare — design docs are almost always project-scoped). `skip task-close` writes the doc but leaves the task in `in_progress` (useful when the decision landed but more work under the same task is pending).

On confirm:

1. `create_document({ title, summary, content, folder, tags })`. Capture the returned doc ID.
2. `update_project({ id: project_id, documents: { <doc_id>: true } })` to link the doc to the project. (Skip if the user said `skip attach`.)
3. If the user confirmed task-close, `update_task({ id: task_id, status: "done" })` with an implementation note referencing the new doc ID (`Design captured in <doc_id> "<Title>".`). Skip otherwise — the user will close the task themselves when the rest of the work lands.

### 5. Close

One-line acknowledgement. No fanfare.

```
Saved <doc_id> "<Title>" in <folder>, linked to <Project Title>. Task 01K… marked done.
```

Or, when attachment or task-close was skipped:

```
Saved <doc_id> "<Title>" in <folder>. Task left in_progress — close when ready.
```

## Output

- A KB document in the MCP, linked to the project.
- Optionally, the originating design task transitioned from `in_progress` to `done` with a note referencing the doc.
- No source code written. No implementation tasks filed as a side effect (unless the conversation explicitly produced follow-up work — then `/fix` or inline `create_task` for obvious follow-ups, confirmed alongside the doc).

## Principles

- **Design decisions are the user's to make.** The skill loads context, runs research, hosts the conversation, and captures the result. It does not pick a winner between real alternatives. When evidence points hard one way, say so; when it doesn't, leave the fork to the user.
- **Research before the conversation, not during.** The archaeologist exists so the main thread doesn't burn context on a codebase survey mid-conversation. Fire it up front or skip it cleanly; don't half-run a survey inline.
- **Capture at the moment of crystallization.** A decision that sits in a thread for a week rots. The skill's value is moving the decision into the KB the same turn it lands.
- **Match the KB, don't reinvent it.** Existing folders, tags, and title patterns are the right defaults. Look at neighbors before proposing something new.
- **One conversation, one doc.** If the conversation sprawls into multiple decisions, offer to close the current one and open another `/design` pass on a sibling task rather than stuffing everything into one doc.

## Constraints

- **Design-category tasks only.** If the dispatched task is any other category, surface that and stop. `/design` is scoped.
- **No writes before confirm.** The doc, the project link, and the task-close all pass through a single visible confirm block. No silent captures.
- **No source code.** The skill produces a document; it never edits application code. If the decision implies code changes, file them as new implementation tasks with a `blocks` edge from the implementation to this design task's output (or, more commonly, file them after the design task closes and the new tasks can reference the published doc).
- **No autonomous fork resolution.** If the user punts on a fork (`we'll figure that out later`), file a follow-up design task rather than guessing the answer in the doc. The doc should reflect what was decided, not what was hoped.
- **Readiness bar is non-negotiable.** Even at invocation: a below-bar design task doesn't get a conversation, it gets pointed at `/backlog`.
- **Archaeologist dispatches are single-shot.** One `task_id` in, one brief out. The skill does not loop on the archaeologist or fire it mid-conversation — if the conversation reveals the brief missed a constraint, the user notes it directly and the skill captures the correction in the final doc.
