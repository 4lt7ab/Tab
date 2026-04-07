# Usage Walkthrough: A Project Management Workflow

This walkthrough follows a developer through a complete project lifecycle using Tab for Projects -- from initial idea to tracked, planned, validated, and documented work. Every step shows what the user does, what the developer agent says, and what happens behind the scenes.

The scenario is generic: a developer wants to add a new feature and uses the plugin to organize, plan, and track the work. The specifics do not matter -- the workflow is the same whether you are building an API, a UI component, or a data pipeline.

---

## Step 1 -- Starting a Session

You open Claude Code. The developer agent activates and runs its bootstrap sequence.

**Behind the scenes:**

1. The developer agent calls `list_projects` with `limit: 1` to verify the Tab for Projects MCP is connected. If this call fails, it tells you the MCP is not available and stops -- it does not improvise alternatives.
2. It resolves which project you are working on. If your codebase's `CLAUDE.md` contains a project slug, it matches against that. If you name a project, it searches the project list. If it is ambiguous, it asks.
3. Once resolved, it shows you a brief overview: the project's goal, what is in flight, and anything that needs attention.

**What you see:**

> **You:** Let's work on the notifications project.
>
> **Developer:** Tracking **notifications-api**. Goal: add real-time notification support to the platform.
>
> 3 tasks in progress, 5 todo. Two tasks have no plan yet -- want to start there, or something else?

The developer agent holds the `project_id` for the rest of the session. Every subsequent operation -- creating tasks, listing work -- scopes to this project automatically.

---

## Step 2 -- Creating a Project

If the project does not exist yet, you describe what you want to build and the developer agent creates it.

> **You:** I want to add webhook support so external services can subscribe to events in our system.
>
> **Developer:** Got it. I'll create a project for this.

**Behind the scenes:**

The developer agent calls `create_project` with the information you provided. It captures:

- **title** -- a short, scannable name for the project.
- **goal** -- the strategic "why" behind the work.
- **requirements** -- what the system needs to do, drawn from what you said.

The developer agent does not fabricate fields you did not provide. If you only described the goal, that is all it fills in. Empty fields are honest; invented ones are noise.

> **Developer:** Created **webhook-support**. Goal: allow external services to subscribe to system events via webhooks.
>
> No tasks yet. Want to break this down into work?

If you share more context -- design constraints, technical preferences, scope limits -- the developer agent captures that in the project's **requirements** or **design** fields. It updates these fields throughout the session as your thinking evolves. Good context does not evaporate into chat history.

---

## Step 3 -- Planning

You ask to break the work down.

> **You:** Yeah, let's break this into tasks. We'll need registration, delivery, retry logic, and a management UI.
>
> **Developer:** Planning the decomposition now.

**Behind the scenes:**

The developer agent handles decomposition. It:

1. **Gathers context.** Reads the project details, fetches any knowledgebase documents, and lists existing tasks to avoid creating duplicates.
2. **Researches the codebase.** This is the most important step. It finds where the change lives (specific files, modules, layers), understands how things work today (current behavior, data flow, architecture), identifies what touches the affected area (callers, consumers, tests), looks at existing patterns and conventions, and flags what could go wrong. It reads actual code -- plans built on shallow understanding create false confidence.
3. **Decomposes the work** into tasks that are action-oriented (titles start with a verb), right-sized (completable in a focused session), and independent where possible.
4. **Writes an implementation plan** for each task, answering: "If someone sat down to implement this right now, what would they need to know and do?" Plans include the approach, specific file paths, sequencing, patterns to follow, edge cases, and testing strategy.
5. **Writes acceptance criteria** for each task -- specific, testable, complete statements that define what "done" looks like.
6. **Creates the tasks** in the MCP via batch `create_task` calls with all fields populated.
7. **Surfaces unresolved items** -- open questions, assumptions that need validation, risks, and dependencies.

**When planning finishes:**

> **Developer:** Created 6 tasks in two groups:
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
> Open question: the current event system uses synchronous dispatch. The delivery pipeline will need to introduce an async layer -- worth discussing before implementation.

You review, discuss, and adjust. If something is wrong -- a missing task, bad scope, wrong grouping -- you say so and the developer agent updates the MCP directly.

---

## Step 4 -- Refinement

Before implementation, you walk through the backlog to make sure every task is understood, scoped, and actionable.

> **You:** Let's refine the webhook-support backlog.

**Behind the scenes:**

The developer agent:

1. **Resolves the project** by matching the argument against the project list.
2. **Loads project context** -- goal, requirements, design -- to evaluate whether tasks align with the project's intent.
3. **Lists the active backlog** -- tasks with status `todo` or `in_progress`.
4. **Presents a session overview:**

> **Developer:** Refinement session for **webhook-support**.
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
> All tasks have plans. Want to walk through them in order, focus on a group, or start with the ones that need the most attention?

**The refinement loop:**

For each task you want to refine, the developer agent pulls full details and works through it with you:

> **You:** Let's look at the delivery pipeline task.
>
> **Developer:** **Build async delivery pipeline** -- high effort, high impact.
>
> Description: Introduce an async dispatch layer between the event system and webhook delivery. Current events fire synchronously; webhooks need non-blocking delivery with independent failure handling per subscriber.
>
> Plan covers: adding a queue abstraction, a delivery worker, payload serialization, and timeout handling. Acceptance criteria include: events dispatched within 100ms, delivery failures isolated per subscriber, queue survives process restart.
>
> What do you think -- does the scope feel right?

> **You:** The queue surviving process restart feels like scope creep for v1. Let's use an in-memory queue first and track persistence as a follow-up.

> **Developer:** Makes sense. I'll update the task to scope it to in-memory only and create a separate task for queue persistence.

The developer agent updates the task immediately via `update_task` -- refined description, adjusted acceptance criteria, updated effort estimate. It also creates a new task for the deferred work. Updates happen as you go so nothing is lost if the session is interrupted.

**Ending the session:**

> **Developer:** Refinement complete. 4 tasks refined, 1 new task added (queue persistence follow-up), 2 tasks skimmed with no changes.
>
> The delivery pipeline task was rescoped to in-memory only -- effort dropped from high to medium. All tasks have plans and acceptance criteria.
>
> Ready to start implementation?

---

## Step 5 -- Implementation

With a refined backlog, you pick a task and start building.

> **You:** Let's start on the webhook event schema task.
>
> **Developer:** On it.

The developer agent reads the task plan, gathers context from linked KB documents and the codebase, implements the solution, runs tests, and commits.

When implementation finishes:

> **Developer:** Completed the schema task. Defined the webhook event schema with types for subscription, delivery, and retry events. Tests passing. Want to move on to the registration endpoint?

The task's status is updated to `done` and the `implementation` field records what was actually built -- this becomes important later for knowledge capture about what happened versus what was planned.

---

## Step 6 -- Knowledge Capture

Once the work is complete, you capture what was learned. The developer agent handles knowledge capture inline.

> **You:** The webhook core is done. Let's capture what we learned.
>
> **Developer:** Capturing knowledge from the completed webhook tasks.

**Behind the scenes:**

Knowledge capture proceeds as follows:

1. **Gathers context.** Fetches full task records -- the `plan` and `implementation` fields are the richest source, showing what was intended versus what actually happened. Scans the existing knowledgebase to understand what is already captured.
2. **Reads the codebase.** Reads the files that were changed, looks for patterns (naming, module structure, conventions), decisions (where implementation diverged from plan and why), gotchas (non-obvious constraints, things that would trip someone up), and integration seams. The code is the source of truth -- task records are summaries.
3. **Checks before writing.** If a document already covers the topic, it updates the existing document rather than creating a duplicate. The knowledgebase should grow in depth, not just breadth.
4. **Writes focused knowledge documents.** Each document covers a single topic: an architecture decision, an established pattern, a gotcha, a design trade-off, or an integration point. Documents are tagged appropriately and written for future consumption -- precise, concrete, referenceable.
5. **Attaches new documents to the project** via `update_project` with `attach_documents`.

**When knowledge capture finishes:**

> **Developer:** Knowledge capture complete. 2 new documents created, 1 existing document updated:
>
> - **Created:** "Async delivery pattern" -- documents the queue-based dispatch approach, why synchronous dispatch was replaced, and the in-memory vs. persistent trade-off.
> - **Created:** "Webhook retry conventions" -- exponential backoff parameters, max retry count, failure isolation per subscriber.
> - **Updated:** "Event system architecture" -- added webhook integration points and delivery flow to the existing event system doc.

These documents are now part of the project's knowledgebase. The next time you plan or build, the developer agent will have access to them -- referencing them in future design decisions, verifying them against code changes, and linking them to new tasks. Every document makes future cycles smarter.

---

## What Just Happened

You went from a rough idea ("add webhook support") to tracked, planned, implemented, and documented work.

Here is the full loop:

1. **Session start.** The developer agent verified the MCP connection, resolved the project, and showed you the current state.

2. **Project creation.** You described what you wanted to build. The developer agent captured it as a project with a goal and requirements.

3. **Planning.** The developer agent decomposed the work into dependency-ordered tasks with plans and acceptance criteria, reading the codebase and KB documents.

4. **Refinement.** You walked through the backlog with the developer agent. Tasks were clarified, rescoped, and updated in real time.

5. **Implementation.** The developer agent gathered context from the task plan and linked KB documents, implemented the solution, tested, and committed.

6. **Knowledge capture.** Post-implementation capture extracted decisions, patterns, and gotchas from completed tasks and the codebase, writing them into the project's knowledgebase -- making future runs smarter.

The plugin has one agent (developer) that handles project management, planning, KB curation, and codebase work. You stay in the driver's seat throughout.

The knowledge loop is the key insight: knowledge captured after implementation feeds future runs, producing better designs, more accurate codebase docs, and more grounded task plans. The system gets smarter about your project as you use it.
