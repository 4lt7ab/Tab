# Project Agents

Tab for Projects uses a hierarchy of eight agents to manage project work. The **manager** is the entry point — it owns the conversation with the user and delegates work to seven specialist agents: the **team-lead**, **planner**, **QA**, **documenter**, **coordinator**, **bugfixer**, and **implementer**. Most agents run asynchronously in the background so the main conversation thread is never blocked — the exceptions are the bugfixer and team-lead, which run in the foreground and talk directly to the user.

```
User <--> Manager <--> MCP (projects, tasks, documents)
              |
              +--> Team-Lead    (foreground — talks to user)
              +--> Planner      (background)
              +--> QA           (background)
              +--> Documenter   (background)
              +--> Coordinator  (background)
              +--> Implementer  (background)
              +--> Bugfixer     (foreground — talks to user)
```

The manager never touches the codebase. Background agents never talk to the user — they return results to the manager, which summarizes them. The team-lead and bugfixer are exceptions: they run in the foreground and interact with the user directly. All communication between layers flows through the manager, and all persistent state lives in the MCP.

---

## Manager

### Purpose

The manager is a conversational project management agent. It gives the Tab for Projects MCP a natural-language interface — helping users organize thinking, capture decisions, track work, and maintain context across sessions. It is a thinking partner, not a sprint planning bot.

### The Hard Rule

The manager does exactly two things:

1. **Talks to the user** — conversation, decisions, context capture.
2. **Talks to the MCP** — CRUD on projects, tasks, and documents.

It never touches the codebase directly. Any work that requires reading files, searching code, running commands, building features, or running tests is delegated to a background subagent.

### Getting Started

When a session begins, the manager follows a three-step bootstrap:

1. **Check the MCP.** Call `list_projects` with `limit: 1`. If the tool is unavailable or fails, inform the user and stop. No improvised alternatives.
2. **Resolve the project.** Match a project by name (if the user provides one), by slug in the codebase's `CLAUDE.md`, or by showing the user a list and asking. Once resolved, the `project_id` is held for the session.
3. **Show the overview.** Confirm which project is active and display the current state — goal, in-flight work, and anything that needs attention.

### Delegation Pattern

When work needs to happen in the codebase, the manager:

1. **Spawns a subagent in the background** (`run_in_background: true`), providing the subagent with a scoped prompt that includes what to do, project context, task context, and relevant knowledgebase document IDs.
2. **Tells the user** briefly what was kicked off — one line, not a ceremony.
3. **Summarizes the result** when the subagent completes.

Independent work items are spawned as parallel background agents in a single message. The manager also supports ad-hoc subagents for generic codebase work (exploring code, running commands, building features) that does not fit the six named agent roles.

When passing knowledgebase documents to subagents, the manager passes document IDs only — it does not fetch document content into the main thread, since documents can be up to 100k characters. The subagent fetches what it needs. The exception is when the user explicitly asks to see a document, in which case the manager calls `get_document` directly.

### The Three MCP Layers

The manager operates on three layers of persistent state:

| Layer | What It Is | Key Fields |
|-------|-----------|------------|
| **Projects** | Top-level container. Captures the strategic "why." | title, goal, requirements, design |
| **Tasks** | Unit of trackable work inside a project. | title, description, plan, implementation, acceptance_criteria, effort, impact, category, group_key, status |
| **Documents** | Independent knowledgebase entities linked to projects via a many-to-many relationship. | title, content (up to 100k chars), tags |

Projects capture why work is happening. Tasks capture what work exists and how it will be done. Documents capture what was learned so future agents are smarter.

Documents are standalone entities — `create_document` does not accept a project ID. New documents must be linked to a project via `update_project(attach_documents: [doc_id])` after creation. The manager uses `list` calls for scanning and `get` calls only when detail is needed, and defaults to showing only `todo` and `in_progress` tasks unless the user asks for history.

---

## Team-Lead

### Purpose

The team-lead is a conversational technical lead who handles ad-hoc requests through knowledgebase expertise. It fills the gap between the manager's hands-off dispatch and the planner's full scope decomposition. Where the manager orchestrates and the planner decomposes, the team-lead converses — it talks to the user, understands what they need, checks documentation for context, and turns requests into actionable work.

The team-lead's primary expertise is the knowledgebase. It knows what's documented, can pull up relevant architecture decisions, conventions, and feature docs to inform its work. It uses this documentation-first understanding to write tasks that are grounded in project context.

### When It Runs

The manager spawns the team-lead (`subagent_type: "tab-for-projects:team-lead"`) when:

- The user has an ad-hoc request that needs scoping and task creation (e.g., "fix the auth redirect," "add a loading spinner").
- The request does not warrant full scope decomposition through the planner pipeline.

It runs in the **foreground** — the team-lead takes over the conversation and talks directly to the user.

### What It Does

1. **Converses.** Talks with the user to understand what they need. Asks clarifying questions before creating work. Reflects intent back to confirm.

2. **Researches.** Searches the knowledgebase for relevant architecture decisions, conventions, and feature docs. The team-lead understands the project through its documentation, not through deep codebase exploration.

3. **Refines.** Turns user requests into developer-ready tasks with descriptions, plans, acceptance criteria, and effort estimates. Grounds tasks in knowledgebase context. Never creates tasks without explicit user permission.

4. **Dispatches.** Spawns developer agents with clear briefs when tasks are ready for implementation.

5. **Catalogues.** Identifies technical debt and bugs during conversations and logs them as tasks for later planning, with user permission.

### Constraints

- **Never creates tasks without explicit permission.** The user must say "create a task," "get this done," or grant standing permission. Without it, the team-lead describes the task and asks.
- **Never writes architecture decisions.** If the question is architectural, it recommends the designer. The team-lead references existing decisions — it does not make new ones.
- **Never decomposes project scope into task graphs.** Single ad-hoc tasks only. Full decomposition is the planner's job.
- **Never modifies the codebase directly.** Dispatches developers for implementation.
- **Works from the knowledgebase first.** Before exploring the codebase, checks if the answer is already documented.

### Output

- Developer-ready tasks created in the MCP with descriptions, plans, and acceptance criteria.
- Developer agents dispatched with clear briefs for immediate implementation.
- Technical debt and bug tasks logged in the backlog for later planning.
- A conversational summary of what was created, dispatched, or deferred.

---

## Planner

### Purpose

The planner turns fuzzy intent into structured, actionable work. It researches the codebase, decomposes work into right-sized tasks, writes concrete implementation plans for each one, and defines what "done" looks like with acceptance criteria. The plans it writes become the contract that implementers follow and QA enforces.

### When It Runs

The manager spawns the planner (`subagent_type: "tab-for-projects:planner"`) when:

- The user wants to decompose a piece of work into tasks.
- Existing tasks need implementation plans and acceptance criteria written.

It always runs in the background.

### Input

| Field | Required | Description |
|-------|----------|-------------|
| Project ID | Yes | The project the work belongs to. |
| Work description | One of these | A description of what needs to be broken down and planned. |
| Task IDs | One of these | Existing tasks that need plans and acceptance criteria. Skips decomposition. |
| Project context | No | Goal, requirements, design. If absent, the planner fetches it from the MCP. |
| Constraints | No | Budget, timeline, dependencies, scope limits. |
| Knowledgebase document IDs | No | Documents the planner will fetch and use as additional context. |

### What It Does

1. **Gathers context.** Fetches project details if not provided, reads knowledgebase documents, pulls full records for any referenced tasks, and lists existing tasks to avoid duplication.

2. **Researches the codebase.** This is the most important step. For each piece of work, the planner identifies where the change lives (specific files and modules), how things work today (current behavior, data flow, architecture), what touches the affected area (callers, consumers, tests, configs), what patterns exist in the codebase, and what could go wrong (edge cases, breaking changes, migration concerns). It reads actual code — plans built on shallow understanding create false confidence.

3. **Decomposes the work** (skipped when planning existing tasks). Breaks work into tasks that are action-oriented (titles start with a verb), right-sized (completable in a focused session, meaningful enough to track), independent where possible, and honestly estimated.

4. **Writes implementation plans.** Each plan answers: "If someone sat down to implement this right now, what would they need to know and do?" A plan includes the approach and rationale, specific file paths to touch and what changes in each, sequencing, patterns to follow (referencing existing code), edge cases and risks, and testing strategy. Plans do not include code snippets, vague hand-waving, or scope creep.

5. **Writes acceptance criteria.** Each criterion is specific, testable, complete (covering happy path, error cases, and relevant edge cases), and scoped to the task. These are the contract QA validates against.

6. **Writes to the MCP.** New tasks are created with all fields populated via batch `create_task` calls. Existing tasks are updated with `plan` and `acceptance_criteria` via batch `update_task` calls — other fields are not changed unless explicitly requested.

7. **Surfaces what is unresolved.** Open questions, assumptions that need validation, risks, dependencies, and anything that could not be determined from the codebase.

### Output

- New tasks created in the MCP (when decomposing work), or updated `plan` and `acceptance_criteria` fields on existing tasks (when planning existing tasks).
- A summary returned to the manager covering what was planned, what was created or updated, and any unresolved items.

---

## QA

### Purpose

The QA agent validates correctness, completeness, and coverage. It inspects both MCP records and the actual codebase to determine whether work is correct, complete, and safe. For every issue it finds, it either updates the relevant task or creates a new one. It validates — it does not redesign.

### When It Runs

The manager spawns the QA agent (`subagent_type: "tab-for-projects:qa"`) when:

- The user wants to validate completed work on one or more tasks.
- The user wants to review a group of related tasks for coverage and integration.
- The user wants a full project plan audit.

It always runs in the background.

### Input

| Field | Required | Description |
|-------|----------|-------------|
| Project ID | Yes | The project to validate. |
| Scope | Yes | One of: specific **task IDs**, a **group key**, or **"full"** for the entire project. |
| Project context | No | Goal, requirements, design. If absent, the QA agent fetches it from the MCP. |
| Focus area | No | A specific concern to weight (e.g., "test coverage", "error handling", "security"). Analysis is weighted toward the focus but does not ignore other critical issues. |
| Knowledgebase document IDs | No | Documents the QA agent will fetch and use as additional context. Architecture docs and conventions are especially valuable. |

### What It Does

1. **Builds the full picture.** Fetches project context if needed, pulls full task records for everything in scope, reads knowledgebase documents, and synthesizes what the plan was, what the acceptance criteria are, and what "done" looks like.

2. **Inspects the actual work.** Goes beyond MCP records into the codebase. Reads the files that were supposed to change, verifies changes exist and match the plan, checks each acceptance criterion against the code, looks at integration seams where changed code meets unchanged code, and checks for obvious missing elements the plan did not mention but the code needs.

3. **Assesses each task** with one of three verdicts:

   - **pass** — work meets its plan and acceptance criteria. No issues found.
   - **pass-with-notes** — work is fundamentally correct but has minor issues, suggestions, or observations worth recording. Nothing blocks shipping.
   - **fail-with-reasons** — work does not meet its plan or acceptance criteria, or introduces problems. Each reason is specific and traceable to something found in the code.

4. **Assesses coverage** (multi-task and full-project scope only). Looks for integration gaps between tasks, missing prerequisites, untested paths, dependency risks, and systemic issues across multiple tasks.

5. **Makes it actionable.**
   - **Failed tasks** are updated via the MCP: status set back to `todo`, findings added with specifics on what failed and what needs to change.
   - **Gaps discovered** become new tasks created with `group_key: "qa-findings"`, making them easy to filter and review. Each gap task has an action-oriented title, a description explaining what is missing and why it matters, and honest effort/impact estimates.

### Output

- Updated tasks in the MCP (failed tasks reset to `todo` with findings).
- New tasks created with `group_key: "qa-findings"` for discovered gaps.
- A summary returned to the manager covering: scope reviewed, per-task verdicts, gaps found (count and highlights), and an overall assessment of whether the work is ready to ship, close to ready, or needs significant rework.

---

## Documenter

### Purpose

The documenter closes the knowledge loop. It reads completed tasks and the actual codebase, extracts architectural decisions, patterns, and rationale that emerged during implementation, and writes them into the project's knowledgebase as MCP documents. Every document it writes makes future planner and QA runs smarter.

Its audience is future agents — planners, QA, other documenters. It writes internal knowledge artifacts, not user-facing documentation or READMEs.

### The Hard Rule

The documenter does exactly two things:

1. **Reads** — tasks (especially completed ones), the codebase, and existing knowledgebase documents.
2. **Writes knowledge** — creates and updates MCP documents, and attaches new documents to the project.

It does not write code or modify tasks.

### When It Runs

The manager spawns the documenter (`subagent_type: "tab-for-projects:documenter"`) when:

- Work is completed and the knowledge should be captured.
- The user wants a specific angle documented (e.g., "capture the auth pattern", "document the testing conventions").

It always runs in the background.

### Input

| Field | Required | Description |
|-------|----------|-------------|
| Project ID | Yes | The project to document. |
| Task IDs | Yes | Completed tasks whose work should be documented. These are the trigger. |
| Project context | No | Goal, requirements, design. If absent, the documenter fetches it from the MCP. |
| Focus area | No | A specific angle to document. |
| Knowledgebase document IDs | No | Existing documents to review before writing, to update rather than duplicate. |

### What It Does

1. **Gathers context.** Fetches full task records (the `plan` and `implementation` fields are the richest source of intended vs. actual), project context if needed, and the current knowledgebase landscape via `list_documents`.

2. **Researches the codebase.** Reads the files that were changed (referenced in task `implementation` fields), looks for patterns (naming, module structure, conventions), decisions (where implementation diverged from plan and why), gotchas (non-obvious constraints, things that would trip someone up), and integration seams.

3. **Checks before writing.** Scans existing documents to decide whether to update an existing document or create a new one. The knowledgebase should grow in depth, not just breadth — ten well-maintained documents beat fifty stale ones.

4. **Writes the knowledge.** Each document focuses on a single topic. Categories of knowledge captured:

   | Category | Example |
   |----------|---------|
   | Architecture decisions | "Chose event-driven over polling for sync because..." |
   | Patterns established | "All MCP tool handlers follow: validate, fetch, transform, respond" |
   | Gotchas | "MCP API returns dates as ISO strings without timezone — always treat as UTC" |
   | Design trade-offs | "Chose simplicity over flexibility — if we need more than 3 doc types, refactor to a registry" |
   | Integration points | "Planner agent depends on task.description being non-empty" |

   Documents are tagged with 1-3 tags from a consistent set: `architecture`, `patterns`, `decisions`, `conventions`, `gotchas`, `integration`.

5. **Create-then-attach.** Since `create_document` produces a standalone document (it does not accept a `project_id`), the documenter must follow a two-step process for every new document:
   1. Call `create_document` with `title`, `content`, and `tags`.
   2. Immediately call `update_project` with `attach_documents: [doc_id]` to link the new document to the project.

   Without the attach step, the document is an orphan — invisible to future agents querying the project's knowledgebase. Existing documents that are updated do not need re-linking.

### Output

- New or updated knowledgebase documents in the MCP, all linked to the project.
- A summary returned to the manager covering: documents created vs. updated, a brief list of what was documented (one line per document), and any knowledge gaps that could not be filled.

---

## Coordinator

### Purpose

The coordinator is a headless agent that reads a project's full state — knowledgebase, backlog, and goals — and synthesizes it into actionable intelligence. Where the manager's input is the user, the coordinator's input is the project itself. It assesses what needs attention, identifies gaps and misalignment, and either reports its findings or acts directly on what it can.

The coordinator operates in two modes. In **report mode**, it analyzes the project and returns a structured assessment — the caller decides what to do with it. In **coordinate mode**, it analyzes, takes direct MCP actions on what it can (archiving duplicates, fixing statuses, creating tasks for gaps), and returns dispatch instructions for specialist work that requires other agents.

### When It Runs

The manager spawns the coordinator (`subagent_type: "tab-for-projects:coordinator"`) when:

- The project needs an overall health assessment (backlog quality, knowledgebase coverage, goal alignment).
- The `/autopilot` skill is invoked — the coordinator runs first in coordinate mode to assess and triage before other agents are dispatched.
- The manager needs to understand what work is ready, stale, or missing before making recommendations to the user.

It always runs in the background.

### Input

| Field | Required | Description |
|-------|----------|-------------|
| Project ID | Yes | The project to assess. |
| Scope | Yes | One of: `"full"` (entire project), a **group key**, specific **task IDs**, or a **question** (e.g., "what's stale?", "what's ready for implementation?"). |
| Mode | Yes | `"report"` (analysis only) or `"coordinate"` (analysis plus direct action and dispatch instructions). |
| Project context | No | Goal, requirements, design. If absent, the coordinator fetches it from the MCP. |
| Knowledgebase document IDs | No | Documents to read for context. If not provided, the coordinator discovers them via `list_documents`. |

### What It Does

1. **Loads context.** Fetches project details, reads knowledgebase documents (unlike the manager, the coordinator reads document content freely — documents are its primary input), and pulls the full backlog.

2. **Builds a mental model.** Synthesizes what the project wants to be, what has been done, what is planned, and where the gaps are between intent and reality.

3. **Assesses project health.** Evaluates backlog health (underspecified tasks, stale work, duplicates, missing work), knowledgebase health (undocumented decisions, stale docs, knowledge gaps), alignment (does the backlog deliver the project goal?), and readiness (which tasks are ready to implement, which need planning, which need QA, which need documentation).

4. **Acts or reports.** In report mode, returns a structured assessment with a summary, prioritized findings, concrete recommendations, and a readiness snapshot. In coordinate mode, takes direct MCP actions (archiving duplicates, fixing statuses, creating gap tasks) and returns a `dispatch` object with four arrays — `plan`, `qa`, `document`, and `implement` — each containing task IDs and context for the specialist agents that should handle them.

### Output

- **Report mode:** A structured assessment with summary, findings, recommendations, and readiness snapshot. References specific task IDs and document titles.
- **Coordinate mode:** A summary of direct actions taken (tasks created, statuses fixed, duplicates archived) plus a `dispatch` object with instructions for planner, QA, documenter, and implementer agents. The caller uses these instructions to spawn the right agents with the right scope.

---

## Bugfixer

### Purpose

The bugfixer is a foreground agent that pair-programs with the user to hunt and fix bugs in real time. Unlike every other subagent, the bugfixer talks directly to the user — it runs in the foreground, not the background. It reads code, runs tests, writes fixes, hunts edge cases, and tracks everything in the MCP.

The bugfixer is designed to make bug hunting feel productive and fun. It operates in a tight find-fix-verify loop: find a bug, fix it right there, verify the fix with tests, and move on. Bugs that are too big to fix in-session get logged as MCP tasks so they are not lost.

### When It Runs

The manager spawns the bugfixer (`subagent_type: "tab-for-projects:bugfixer"`) when:

- The user invokes the `/bugfix` skill.
- The user explicitly wants a collaborative bug-hunting session.

It runs in the **foreground** (`run_in_background: false`) — the bugfixer takes over the conversation and talks directly to the user.

### Input

| Field | Required | Description |
|-------|----------|-------------|
| Project ID | Yes | The project context for the session. |
| Task IDs | No | Known bugs or areas of concern to investigate. |
| Project context | No | Goal, requirements, design. |
| Knowledgebase document IDs | No | Architecture docs and prior analysis that reveal where bugs are likely hiding. |
| Focus area | No | What the user wants to focus on (e.g., "auth module", "the retry logic"). |

### What It Does

1. **Orients.** Fetches knowledgebase documents and task details from the MCP. Assesses the codebase: what is the test setup, what framework, where do tests live, what is the current test baseline (passing, failing). Shares findings with the user briefly.

2. **Sets up the toolkit.** Checks for a `.local/` directory for test scripts, repro helpers, and coverage tools. Creates it if it does not exist. Builds helpers as needed during the session.

3. **Runs the bugfix loop.** A tight, conversational cycle:
   - **Find** — runs tests, reads business logic, checks error handling, follows the user's hunches, reviews test coverage for gaps.
   - **Fix** — fixes bugs immediately rather than deferring. Explains what changed and why.
   - **Verify** — runs relevant tests after every fix. Writes new tests for bugs that lacked them.
   - **Track** — keeps a running tally of bugs found, fixed, and tests added. Creates MCP tasks for anything too big to fix in-session, tagged with `category: "bugfix"`.

4. **Ends the session.** Summarizes bugs found, bugs fixed, tests added, and tools built. Lists deferred items. Notes what is in `.local/` for future reuse. Offers to capture findings in the knowledgebase via the documenter.

### Output

- Bug fixes applied directly to the codebase.
- New tests written for each fix.
- MCP tasks created for bugs too large to fix in-session.
- A session summary covering bugs found, fixed, tests added, tools built, and deferred items.

---

## Implementer

### Purpose

The implementer is a headless agent that turns task plans into working code. It is the bridge between "what we'll build" and "what we built." The plan is the contract — the implementer executes it faithfully, but verifies assumptions against the current codebase first. It self-validates against acceptance criteria before reporting completion.

The implementer does not write plans. If a task has no plan, it flags it and skips it. It does not expand scope — adjacent improvements are reported as suggestions, not applied as code changes.

### When It Runs

The manager spawns the implementer (`subagent_type: "tab-for-projects:implementer"`) when:

- Tasks have implementation plans and acceptance criteria and are ready to be built.
- The `/autopilot` skill reaches its implementation phase — the coordinator identifies ready tasks and the manager dispatches implementer agents in dependency-ordered waves.

It always runs in the background.

### Input

| Field | Required | Description |
|-------|----------|-------------|
| Project ID | Yes | The project the tasks belong to. |
| Task IDs | Yes | Tasks with existing plans to implement. |
| Project context | No | Goal, requirements, design. If absent, the implementer fetches it from the MCP. |
| Knowledgebase document IDs | No | Architecture decisions, conventions, and patterns that inform how to implement correctly. |

### What It Does

1. **Loads context.** Fetches project details, pulls full task records (the `plan` field is its primary input, `acceptance_criteria` is what it validates against), reads knowledgebase documents, and lists surrounding tasks to understand integration context.

2. **Researches the codebase.** Reads the files referenced in the plan, understands patterns in adjacent code, verifies the plan's assumptions against the current state (code may have changed since planning), and identifies callers, consumers, and tests that would be affected.

3. **Implements the plan.** Follows the plan's sequence and approach, respects codebase conventions, makes targeted changes (no "while I'm here" refactors), and resolves ambiguity from acceptance criteria. When implementing multiple tasks, sequences them by dependency and handles file conflicts.

4. **Self-validates.** Goes through each acceptance criterion and verifies the implementation satisfies it. Runs existing tests for changed code. Flags anything uncertain — this is a smoke check, not full QA.

5. **Updates the MCP.** Sets task status to `in_progress` at start, then to `done` on completion. Fills the `implementation` field with what was actually done: files changed, approach taken, deviations from plan and why.

### Output

- Code changes applied to the codebase following the task plans.
- Updated MCP task records with `status: "done"` and filled `implementation` fields.
- A summary returned to the manager covering: tasks completed, tasks partially completed, tasks not started (with reasons), deviations from plans, issues discovered, self-validation results, and scope suggestions.

---

## Agent Interaction Flow

A typical lifecycle from idea to documented work:

1. **User describes work to the manager.** "I want to add webhook support to the API."

2. **Manager captures context.** Updates the project's goal/requirements/design fields in the MCP if the user shares strategic information. Discusses scope and approach with the user.

3. **Manager spawns the planner.** Provides the project ID, work description, project context, and relevant knowledgebase document IDs. The planner runs in the background.

4. **Planner researches and decomposes.** Reads the codebase to understand the current architecture, breaks the work into tasks, writes implementation plans and acceptance criteria, and creates the tasks in the MCP. Returns a summary to the manager.

5. **Manager relays the plan.** Summarizes what the planner created — task count, groupings, any open questions or risks. The user reviews, discusses, and adjusts.

6. **Implementation happens.** The user works through the tasks directly, or the manager spawns the **implementer** in the background to execute task plans. The implementer follows each plan, self-validates against acceptance criteria, and updates task statuses and implementation fields in the MCP. Task statuses move from `todo` to `in_progress` to `done`.

7. **Manager spawns QA.** Provides the project ID, task IDs (or group key, or "full"), project context, and any focus areas. QA runs in the background.

8. **QA validates.** Reads the MCP records and the actual codebase, assesses each task (pass / pass-with-notes / fail-with-reasons), checks for integration gaps and missing coverage. Failed tasks are reset to `todo` with findings. New tasks are created under `group_key: "qa-findings"` for discovered gaps. Returns a summary to the manager.

9. **Manager relays findings.** Summarizes verdicts and gaps. The user addresses failures and QA findings, cycling back through implementation and QA as needed.

10. **Manager spawns the documenter.** Provides the project ID, completed task IDs, project context, and existing knowledgebase document IDs. The documenter runs in the background.

11. **Documenter captures knowledge.** Reads completed tasks and the codebase, extracts decisions, patterns, and gotchas, creates or updates knowledgebase documents, and attaches new documents to the project. Returns a summary to the manager.

12. **Knowledge feeds future work.** The documents the documenter wrote are now available to the planner and QA on the next cycle — making their research richer and their outputs more grounded in project history.

### Alternative Paths

**Coordinator-driven assessment.** The manager can spawn the coordinator at any point to assess project health, identify stale or missing work, and produce dispatch instructions for other agents. The `/autopilot` skill uses this as its first phase — the coordinator assesses the full project in coordinate mode, takes direct MCP actions, and returns structured dispatch instructions that the manager uses to spawn planner, QA, documenter, and implementer agents in parallel.

**Bugfix sessions.** When the user wants to hunt bugs rather than follow the plan-implement-validate cycle, the `/bugfix` skill spawns the bugfixer in the foreground. The bugfixer pair-programs with the user directly — finding, fixing, and verifying bugs in real time. This is an alternative path that bypasses the normal delegation pattern: the bugfixer talks to the user, not the manager.
