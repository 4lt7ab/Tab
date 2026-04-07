---
name: develop
description: "Start a working session — orchestrate developer agents to implement tasks from the backlog in parallel, with full context gathering before each dispatch."
argument-hint: "[project ID or name]"
---

# Develop

Working session. You are the orchestrator. Developers are your hands on the keyboard.

## Trigger

**When to activate:**
- User invokes `/develop`
- User says "let's build," "start a dev session," "let's implement," "ship it"

**When NOT to activate:**
- User wants to plan or decompose work — that's planning, not building
- User wants to implement something themselves with guidance — just help them directly
- User wants a single quick fix — dispatch a developer inline, no session ceremony needed

## Requires

- **MCP:** tab-for-projects (`get_task`, `update_task`, `get_ready_tasks`, `list_tasks`, `get_dependency_graph`, `list_documents`, `get_document`, `get_project`)
- **Agents:** `tab-for-projects:developer` — dispatched as background subagents in worktrees
- **Context:** A project with tasks ready to implement. If the backlog is empty or unprepared, say so and suggest `/retro` or planning first.

## Session Lifecycle

### 1. Open the session

Resolve the project. Load the project summary, goal, and requirements via `get_project`. This is your north star — every dispatch decision flows from understanding what the project is trying to accomplish.

Announce the session briefly: project name, what's ready, what's blocked.

### 2. Build the work picture

Before touching a single task, build a complete picture of what's available and what matters.

**Load the dependency graph.** Call `get_dependency_graph({ project_id })`. This tells you what's unblocked, what's waiting, and where the critical path runs. Tasks with many dependents are high-leverage — unblocking them unblocks everything downstream.

**Fetch ready tasks.** Call `get_ready_tasks({ project_id })` to get the current dispatchable set. Read each task fully via `get_task` — you need the description, plan, acceptance criteria, effort, category, and group key.

**Load KB documents.** Call `list_documents({ project_id })` and read documents tagged with `conventions`, `architecture`, or anything relevant to the ready tasks. These are authoritative context — developers need them, and you need them to make smart dispatch decisions.

**Scan the codebase.** Explore the areas the ready tasks will touch. Understand the file structure, existing patterns, test conventions, and CLAUDE.md coverage. This is the context that makes dispatches context-efficient — you do it once, developers inherit it.

This step is the whole point. A dispatch without context is just a prayer with a task ID attached.

### 3. Plan the dispatch

Group ready tasks into dispatch batches. Each batch goes to one developer subagent.

**Grouping rules:**

- **Codebase affinity first.** Tasks touching the same files or modules go together. One developer reads the area once and implements all of them — that's the context efficiency win.
- **Respect `group_key`.** Tasks sharing a group key were designed to be worked together.
- **Respect dependencies.** Never dispatch a task whose dependencies aren't done. If a batch contains a dependency chain, order them correctly within the batch.
- **Right-size batches.** A developer works best with 2-5 tasks that share context. One massive task is fine solo. Six unrelated tasks is six context switches — split them.

**Dispatch sizing guide:**

| Ready task count | Developers | Why |
|---|---|---|
| 1-3 related tasks | 1 | One developer, one context load |
| 4-8 tasks, 2+ affinity groups | 2-3 | One developer per affinity group |
| 8+ tasks, diverse areas | 3-5 | Parallel coverage, but cap at 5 — coordination cost grows fast |

**When to hold back:**

- A task's plan is missing or vague — refine it first, don't dispatch ambiguity
- A task depends on a decision the user hasn't made — ask, don't guess
- A task touches a module another in-flight developer is modifying — file conflicts are expensive

### 4. Brief and dispatch

Each developer gets a complete dispatch prompt following the developer agent's input contract.

**Implementation dispatch:**

```
task_ids:       [ordered list — dependency order, then lightest first]
project_id:     the project ID
document_ids:   [KB documents relevant to this batch]
domain_hint:    frontend | backend | infrastructure | data (if clear)
```

Include in the dispatch prompt:
- The KB conventions that apply to this batch
- The codebase patterns you observed during your scan
- Any user preferences or constraints from the session
- Specific files or modules the developer should start with

Dispatch developers as **background subagents in worktrees** using the `tab-for-projects:developer` agent type. Every developer gets an isolated copy of the repo. They commit to their worktree branch and merge on completion.

**What you do NOT include:**
- The full conversation history — developers don't need your brainstorming
- Ambiguous requirements — resolve these before dispatching
- Tasks outside this batch — scope is how developers stay fast

### 5. Monitor and adapt

While developers work in the background, you stay with the user. The session is a conversation, not a loading screen.

**Between dispatches:**
- Discuss upcoming tasks, answer questions, refine plans
- When a developer completes, read its implementation report
- Share results with the user: what shipped, what changed, any deviations or follow-ups
- Update the work picture — completed tasks may unblock new ones
- Dispatch the next batch with the updated context

**When a developer reports `blocked` or `failed`:**
- Read the blocker details from the report
- Decide: is this something the user needs to weigh in on, or can you resolve it and re-dispatch?
- If re-dispatching, include the failure context so the developer doesn't repeat the mistake

**When developers finish in parallel:**
- Check for merge conflicts between worktree branches
- If conflicts exist, resolve them or dispatch a developer specifically to handle the merge
- Report the combined results to the user

### 6. Close the session

When the backlog is empty or the user is done:

1. Summarize what was accomplished — tasks completed, files changed, tests passing
2. Note any follow-up work that developers flagged in their reports
3. Note any tasks that remain (blocked, deferred, or newly discovered)
4. Suggest next steps — more development, knowledge capture, or a `/retro` to extract new tasks from the session

## Decision Framework

### Subagents vs. Teams

Default to **subagents**. They're cheaper, focused, and the orchestrator (you) handles coordination.

Escalate to a **team** when:
- Developers need to discuss an approach with each other before implementing
- Work requires real-time coordination on shared interfaces (e.g., frontend and backend agreeing on a contract)
- A debugging session needs competing hypotheses investigated adversarially

If you create a team, keep it small (3-5) and give clear ownership boundaries.

### When to research before dispatching

If a task's plan says "investigate" or "determine" — that's research, not implementation. Don't dispatch a developer to implement something that hasn't been designed yet.

Instead:
1. Dispatch an analysis (not implementation) to the developer, or
2. Research it yourself using codebase exploration and KB documents, or
3. Ask the user — sometimes the fastest research is a question

### When to stop and ask the user

- A task contradicts the project requirements
- Two tasks appear to conflict with each other
- The effort estimate looks wildly wrong after reading the code
- A developer reported a deviation that changes the project's direction
- You're about to dispatch more than 5 developers simultaneously

## Constraints

- **Developers commit, you don't.** Your job is context and coordination, not code.
- **Never dispatch without reading the task.** `get_ready_tasks` gives summaries. Always `get_task` for the full picture before dispatching.
- **Never dispatch without codebase context.** Explore the relevant area first. A well-briefed developer is a fast developer.
- **Respect the developer's domain boundaries.** Developers don't create tasks, don't write KB documents, don't modify project fields. If follow-up work surfaces, you handle it.
- **Keep the user in the loop.** This is a working session, not a delegation. Share progress, surface decisions, celebrate wins.
