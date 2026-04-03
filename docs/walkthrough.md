# Usage Walkthrough: A Project Management Workflow

This walkthrough follows a developer through a complete project lifecycle using Tab for Projects -- from initial idea to tracked, planned, validated, and documented work. Every step shows what the user does, what the manager says, and what happens behind the scenes.

The scenario is generic: a developer wants to add a new feature and uses the plugin to organize, plan, and track the work. The specifics do not matter -- the workflow is the same whether you are building an API, a UI component, or a data pipeline.

---

## Step 1 -- Starting a Session

You open Claude Code. The manager agent activates and runs its bootstrap sequence.

**Behind the scenes:**

1. The manager calls `list_projects` with `limit: 1` to verify the Tab for Projects MCP is connected. If this call fails, the manager tells you the MCP is not available and stops -- it does not improvise alternatives.
2. It resolves which project you are working on. If your codebase's `CLAUDE.md` contains a project slug, it matches against that. If you name a project, it searches the project list. If it is ambiguous, it asks.
3. Once resolved, it shows you a brief overview: the project's goal, what is in flight, and anything that needs attention.

**What you see:**

> **You:** Let's work on the notifications project.
>
> **Manager:** Tracking **notifications-api**. Goal: add real-time notification support to the platform.
>
> 3 tasks in progress, 5 todo. Two tasks have no plan yet -- want to start there, or something else?

The manager holds the `project_id` for the rest of the session. Every subsequent operation -- creating tasks, spawning agents, listing work -- scopes to this project automatically.

---

## Step 2 -- Creating a Project

If the project does not exist yet, you describe what you want to build and the manager creates it.

> **You:** I want to add webhook support so external services can subscribe to events in our system.
>
> **Manager:** Got it. I'll create a project for this.

**Behind the scenes:**

The manager calls `create_project` with the information you provided. It captures:

- **title** -- a short, scannable name for the project.
- **goal** -- the strategic "why" behind the work.
- **requirements** -- what the system needs to do, drawn from what you said.

The manager does not fabricate fields you did not provide. If you only described the goal, that is all it fills in. Empty fields are honest; invented ones are noise.

> **Manager:** Created **webhook-support**. Goal: allow external services to subscribe to system events via webhooks.
>
> No tasks yet. Want to break this down into work?

If you share more context -- design constraints, technical preferences, scope limits -- the manager captures that in the project's **requirements** or **design** fields. It updates these fields throughout the session as your thinking evolves. Good context does not evaporate into chat history.

---

## Step 3 -- Planning

You ask the manager to break the work down. The manager does not do this itself -- it spawns the **planner** agent in the background.

> **You:** Yeah, let's break this into tasks. We'll need registration, delivery, retry logic, and a management UI.
>
> **Manager:** Kicking off the planner to decompose this into tasks.

**Behind the scenes:**

The manager spawns the planner (`subagent_type: "tab-for-projects:planner"`) with `run_in_background: true`. It passes:

- The **project ID**.
- A **work description** based on what you said.
- **Project context** (goal, requirements, design) so the planner does not have to fetch it.
- **Knowledgebase document IDs** if the project already has relevant documents (architecture docs, conventions, prior research). The manager passes IDs only -- it does not pull document content into the main thread.

While the planner works, the main conversation thread stays free. You can keep talking, ask questions, or work on something else.

**What the planner does (in the background):**

1. **Gathers context.** Reads the project details, fetches any knowledgebase documents, and lists existing tasks to avoid creating duplicates.
2. **Researches the codebase.** This is the most important step. The planner finds where the change lives (specific files, modules, layers), understands how things work today (current behavior, data flow, architecture), identifies what touches the affected area (callers, consumers, tests), looks at existing patterns and conventions, and flags what could go wrong. It reads actual code -- plans built on shallow understanding create false confidence.
3. **Decomposes the work** into tasks that are action-oriented (titles start with a verb), right-sized (completable in a focused session), and independent where possible.
4. **Writes an implementation plan** for each task, answering: "If someone sat down to implement this right now, what would they need to know and do?" Plans include the approach, specific file paths, sequencing, patterns to follow, edge cases, and testing strategy.
5. **Writes acceptance criteria** for each task -- specific, testable, complete statements that define what "done" looks like. These become the contract that QA validates against.
6. **Creates the tasks** in the MCP via batch `create_task` calls with all fields populated.
7. **Surfaces unresolved items** -- open questions, assumptions that need validation, risks, and dependencies.

**When the planner finishes:**

> **Manager:** Planner finished. Created 6 tasks in two groups:
>
> **webhook-core** (4 tasks):
> - Define webhook event schema -- low effort, high impact
> - Implement webhook registration endpoint -- medium effort, high impact
> - Build async delivery pipeline -- high effort, high impact
> - Add retry logic with exponential backoff -- medium effort, high impact
>
> **webhook-ui** (2 tasks):
> - Create webhook management dashboard -- medium effort, medium impact
> - Add delivery log viewer -- low effort, medium impact
>
> Open question: the planner flagged that the current event system uses synchronous dispatch. The delivery pipeline will need to introduce an async layer -- worth discussing before implementation.

The manager relays the summary, not the raw output. You review, discuss, and adjust. If something is wrong -- a missing task, bad scope, wrong grouping -- you tell the manager and it updates the MCP directly.

---

## Step 4 -- Refinement

Before implementation, you run the refinement skill to walk through the backlog and make sure every task is understood, scoped, and actionable.

> **You:** /refinement webhook-support

**Behind the scenes:**

The `/refinement` skill activates. The manager:

1. **Resolves the project** by matching the argument against the project list.
2. **Loads project context** -- goal, requirements, design -- to evaluate whether tasks align with the project's intent.
3. **Lists the active backlog** -- tasks with status `todo` or `in_progress`.
4. **Presents a session overview:**

> **Manager:** Refinement session for **webhook-support**.
> Goal: allow external services to subscribe to system events via webhooks.
>
> 6 tasks in the backlog:
>
> | Task | Effort | Impact | Plan? |
> |------|--------|--------|-------|
> | Define webhook event schema | low | high | yes |
> | Implement webhook registration endpoint | medium | high | yes |
> | Build async delivery pipeline | high | high | yes |
> | Add retry logic with exponential backoff | medium | high | yes |
> | Create webhook management dashboard | medium | medium | yes |
> | Add delivery log viewer | low | medium | yes |
>
> All tasks have plans from the planner run. Want to walk through them in order, focus on a group, or start with the ones that need the most attention?

**The refinement loop:**

For each task you want to refine, the manager pulls full details and works through it with you:

> **You:** Let's look at the delivery pipeline task.
>
> **Manager:** **Build async delivery pipeline** -- high effort, high impact.
>
> Description: Introduce an async dispatch layer between the event system and webhook delivery. Current events fire synchronously; webhooks need non-blocking delivery with independent failure handling per subscriber.
>
> Plan covers: adding a queue abstraction, a delivery worker, payload serialization, and timeout handling. Acceptance criteria include: events dispatched within 100ms, delivery failures isolated per subscriber, queue survives process restart.
>
> What do you think -- does the scope feel right?

> **You:** The queue surviving process restart feels like scope creep for v1. Let's use an in-memory queue first and track persistence as a follow-up.

> **Manager:** Makes sense. I'll update the task to scope it to in-memory only and create a separate task for queue persistence.

The manager updates the task immediately via `update_task` -- refined description, adjusted acceptance criteria, updated effort estimate. It also creates a new task for the deferred work. Updates happen as you go so nothing is lost if the session is interrupted.

If a task touches unfamiliar parts of the codebase, the manager spawns a background research agent to investigate while you keep talking. When findings come back, they fold into the conversation and inform the refinement.

**Ending the session:**

> **Manager:** Refinement complete. 4 tasks refined, 1 new task added (queue persistence follow-up), 2 tasks skimmed with no changes.
>
> The delivery pipeline task was rescoped to in-memory only -- effort dropped from high to medium. All tasks have plans and acceptance criteria.
>
> Want me to run QA to check for gaps across the backlog?

---

## Step 5 -- Implementation

With a refined backlog, you pick a task and start building.

> **You:** I'll work on the webhook event schema task.
>
> **Manager:** Pulling up the details.

The manager calls `get_task` and shows you the full plan -- approach, files to touch, sequencing, patterns to follow, and acceptance criteria. You use this as a guide while you write the code.

The manager itself never touches the codebase. If you want it to help with implementation, it spawns an ad-hoc subagent in the background with a scoped prompt. But the focus of this workflow is on tracking and coordination, not code generation.

As you work, you update the manager on progress:

> **You:** Schema is defined and tests pass. Moving on.
>
> **Manager:** Marked the schema task as done. Want to tackle the registration endpoint next?

The manager updates the task's status to `done` in the MCP. The `implementation` field gets filled with what was actually done -- this field becomes important later when the documenter needs to understand what happened versus what was planned.

---

## Step 6 -- Validation

After completing a set of tasks, you ask the manager to check the work. The manager spawns the **QA** agent in the background.

> **You:** I've finished the four core webhook tasks. Can you validate the work?
>
> **Manager:** Spawning QA to review the webhook-core tasks.

**Behind the scenes:**

The manager spawns the QA agent (`subagent_type: "tab-for-projects:qa"`) with `run_in_background: true`. It passes:

- The **project ID**.
- The **task IDs** for the completed tasks (the scope can also be a group key like `"webhook-core"` or `"full"` for the entire project).
- **Project context** (goal, requirements, design).
- A **focus area** if you have a specific concern (e.g., "error handling", "test coverage").
- **Knowledgebase document IDs** if the project has relevant docs -- architecture and conventions are especially valuable for grounding the review.

**What QA does (in the background):**

1. **Builds the full picture.** Fetches project context, pulls full task records (plan, acceptance criteria, implementation), and reads any knowledgebase documents to understand expectations the code alone does not reveal.
2. **Inspects the actual codebase.** QA goes beyond MCP records. It reads the files that were supposed to change, verifies that changes exist and match the plan, checks each acceptance criterion against the code, looks at integration seams where changed code meets unchanged code, and checks for obvious missing elements the plan did not mention but the code needs.
3. **Assesses each task** with a verdict:
   - **pass** -- work meets its plan and acceptance criteria.
   - **pass-with-notes** -- fundamentally correct, minor observations worth recording.
   - **fail-with-reasons** -- does not meet criteria or introduces problems. Each reason is specific and traceable to code.
4. **Assesses coverage** across the task group: integration gaps, missing prerequisites, untested paths, dependency risks, systemic issues.
5. **Makes it actionable.** Failed tasks are updated in the MCP -- status set back to `todo`, findings added with specifics. Gaps become new tasks created with `group_key: "qa-findings"` so they are easy to find and review.

**When QA finishes:**

> **Manager:** QA review complete for webhook-core:
>
> - **Define webhook event schema** -- pass
> - **Implement webhook registration endpoint** -- pass-with-notes (suggestion: add rate limiting on registration to prevent abuse)
> - **Build async delivery pipeline** -- pass
> - **Add retry logic with exponential backoff** -- fail (retry delay calculation uses linear backoff despite the task specifying exponential; max retry count is not enforced)
>
> 1 new task created under qa-findings:
> - Add rate limiting to webhook registration endpoint (low effort, medium impact)
>
> The retry task has been set back to todo with the specific findings. Overall: close to ready, one task needs a fix.

You address the failure, fix the retry logic, and can run QA again on just that task if you want a recheck. The cycle between implementation and validation repeats as needed.

---

## Step 7 -- Documentation

Once the work is validated and complete, you ask the manager to capture what was learned. The manager spawns the **documenter** agent in the background.

> **You:** The webhook core is done and passing QA. Let's capture what we learned.
>
> **Manager:** Spawning the documenter to capture knowledge from the completed webhook tasks.

**Behind the scenes:**

The manager spawns the documenter (`subagent_type: "tab-for-projects:documenter"`) with `run_in_background: true`. It passes:

- The **project ID**.
- The **task IDs** of completed work to document.
- **Project context** (goal, requirements, design).
- A **focus area** if you want a specific angle documented (e.g., "capture the async delivery pattern").
- **Existing knowledgebase document IDs** so the documenter can update rather than duplicate.

**What the documenter does (in the background):**

1. **Gathers context.** Fetches full task records -- the `plan` and `implementation` fields are the richest source, showing what was intended versus what actually happened. Scans the existing knowledgebase to understand what is already captured.
2. **Researches the codebase.** Reads the files that were changed, looks for patterns (naming, module structure, conventions), decisions (where implementation diverged from plan and why), gotchas (non-obvious constraints, things that would trip someone up), and integration seams. The code is the source of truth -- task records are summaries.
3. **Checks before writing.** If a document already covers the topic, it updates the existing document rather than creating a duplicate. The knowledgebase should grow in depth, not just breadth.
4. **Writes focused knowledge documents.** Each document covers a single topic: an architecture decision, an established pattern, a gotcha, a design trade-off, or an integration point. Documents are tagged (e.g., `architecture`, `patterns`, `decisions`, `conventions`, `gotchas`, `integration`) and written for future agents -- precise, concrete, referenceable.
5. **Attaches new documents to the project.** Since `create_document` produces a standalone document (it does not accept a project ID), the documenter follows a two-step process: create the document, then call `update_project` with `attach_documents` to link it. Without this step, the document would be invisible to future agents querying the project's knowledgebase.

**When the documenter finishes:**

> **Manager:** Documenter complete. 2 new documents created, 1 existing document updated:
>
> - **Created:** "Async delivery pattern" -- documents the queue-based dispatch approach, why synchronous dispatch was replaced, and the in-memory vs. persistent trade-off.
> - **Created:** "Webhook retry conventions" -- exponential backoff parameters, max retry count, failure isolation per subscriber.
> - **Updated:** "Event system architecture" -- added webhook integration points and delivery flow to the existing event system doc.
>
> Knowledge gap noted: the rationale for choosing in-memory over persistent queues was discussed during refinement but not recorded in any task's implementation field. May want to capture that decision explicitly.

These documents are now part of the project's knowledgebase. The next time the planner runs, it will have access to them -- making its plans more grounded in the project's actual architecture and conventions. The next time QA runs, it can validate against documented patterns and decisions. Every document makes future cycles smarter.

---

## What Just Happened

You went from a rough idea ("add webhook support") to tracked, planned, validated, and documented work -- without the manager ever touching the codebase.

Here is the full loop:

1. **Session start.** The manager verified the MCP connection, resolved the project, and showed you the current state.

2. **Project creation.** You described what you wanted to build. The manager captured it as a project with a goal and requirements.

3. **Planning.** The manager spawned the **planner** in the background. The planner researched the codebase, decomposed the work into right-sized tasks, wrote implementation plans and acceptance criteria for each one, and created them in the MCP.

4. **Refinement.** You ran `/refinement` and walked through the backlog with the manager. Tasks were clarified, rescoped, and updated in real time. Research agents ran in the background to answer unknowns while you kept talking.

5. **Implementation.** You worked through tasks using the planner's plans as a guide. The manager tracked progress and updated task statuses.

6. **Validation.** The manager spawned **QA** in the background. QA read the MCP records and the actual codebase, assessed each task against its acceptance criteria, flagged failures with specific reasons, and created new tasks for discovered gaps.

7. **Documentation.** The manager spawned the **documenter** in the background. The documenter read completed tasks and the codebase, extracted decisions, patterns, and gotchas, and wrote them into the project's knowledgebase -- making future planner and QA runs smarter.

The seven agents each play a distinct role:

| Agent | Role | When it runs |
|-------|------|-------------|
| **Manager** | Talks to the user and the MCP. Delegates everything else. | Always active in the main thread |
| **Planner** | Researches the codebase and turns intent into structured tasks with plans and acceptance criteria. | When work needs to be decomposed or planned |
| **QA** | Validates work against plans and acceptance criteria. Creates actionable findings. | When work needs to be reviewed |
| **Documenter** | Captures decisions, patterns, and gotchas into the project knowledgebase. | When knowledge should be preserved |
| **Coordinator** | Reads full project state and produces assessments or dispatch instructions for specialist agents. | When the project needs a health check or `/autopilot` runs |
| **Bugfixer** | Pair-programs with the user to hunt and fix bugs in real time. Runs in the **foreground**. | When the user invokes `/bugfix` |
| **Implementer** | Executes task plans faithfully, self-validates against acceptance criteria. | When planned tasks are ready to be built |

Background agents run asynchronously -- the main conversation thread is never blocked. The one exception is the bugfixer, which runs in the foreground and talks directly to the user. The manager spawns agents, tells you what it kicked off, and relays results when they finish. You stay in the driver's seat throughout.

The knowledge loop is the key insight: documents written by the documenter feed back into future planner and QA runs, making each cycle more informed than the last. The system gets smarter about your project as you use it.

### Alternative Workflows

The walkthrough above follows the manual, step-by-step flow. Two skills offer alternative paths:

**`/autopilot [project-name]`** -- automates the entire cycle. The coordinator assesses the project first (identifying what needs planning, QA, documentation, and implementation), then the manager dispatches planner, QA, documenter, and implementer agents in parallel based on the coordinator's findings. Implementation runs in dependency-ordered waves, followed by a post-implementation QA pass. You can type `/autopilot`, walk away, and come back to a project that has been triaged, planned, implemented, validated, and documented -- with a clear summary of everything that happened.

**`/bugfix [project-name]`** -- starts a hands-on bug-hunting session. Instead of the plan-implement-validate cycle, the bugfixer agent takes over the conversation in the foreground and pair-programs with you in real time. It finds bugs, fixes them immediately, verifies with tests, and tracks everything in the MCP. This is the path to take when you want to hunt bugs collaboratively rather than work through a structured backlog.
