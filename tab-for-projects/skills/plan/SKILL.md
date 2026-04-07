---
name: plan
description: "Design and decompose a feature into implementation tasks within an existing project."
argument-hint: "<feature description> for <project ID or title>"
mode: headless
agents:
  - tech-lead
  - project-manager
requires-mcp:
  - tab-for-projects
---

# Plan — Feature Decomposition

The strategy play. Takes a feature idea within an existing project, has the Tech Lead design it and decompose it into tasks, then runs the Project Manager as a quality gate on the result. Use this when you know what you want to build next but need it broken into implementable pieces with full context.

## Trigger

**When to activate:**
- The user runs `/plan`
- The user says "break down [feature]" or "plan [feature] for [project]"

**When NOT to activate:**
- The user wants to start a brand new project (that's `/kickoff`)
- The user wants to build existing tasks (that's `/build`)
- The user wants a project status check (that's `/status`)

## Arguments

- Requires two pieces: a **feature description** and a **project reference** (ID or title).
- If the feature description is provided but the project is omitted, list projects and ask.
- If neither is provided, ask what they want to plan and for which project.
- The feature description can be brief ("add authentication") or detailed ("add OAuth2 with Google and GitHub providers, JWT session tokens, middleware for protected routes").

## Sequence

1. **Load project context.** Before dispatching agents, Tab gathers:
   - Project goal, requirements, and design (from `get_project`)
   - Existing KB documents (from `list_documents`) — architecture, conventions, prior design docs
   - Current task landscape (from `list_tasks`) — what already exists, what's in progress, what's done

   This context ensures the Tech Lead designs with full awareness of what's already there.

2. **Dispatch Tech Lead** (first pass — design doc) with:
   - `project_id`: the resolved project ID
   - `dispatch_type`: `write`
   - `scope`: the feature to design
   - `context`: the feature description from the user, plus project goal/requirements/design and relevant existing KB document summaries

   The Tech Lead writes a design document grounding the feature in the project's existing architecture and conventions. This doc captures the *how* — approach, trade-offs, key decisions.

3. **Read the Tech Lead's report.** Confirm the design doc was created. Note the document ID for reference.

4. **Dispatch Tech Lead** (second pass — task decomposition) with:
   - `project_id`: the resolved project ID
   - `dispatch_type`: `write`
   - `scope`: "task decomposition for [feature]"
   - `context`: the design document just created (reference by ID), the feature description, existing task landscape (so the TL doesn't duplicate existing tasks), and the instruction to decompose into implementation tasks with: descriptions, plans, acceptance criteria, effort/impact estimates, dependency ordering, and group keys

   The Tech Lead doesn't create tasks directly — it produces a decomposition in its report that the orchestrator routes to the PM.

5. **Dispatch Project Manager** with:
   - `project_id`: the resolved project ID
   - `focus`: `task-shape`

   Provide the Tech Lead's decomposition as context. The PM creates the tasks, wires dependencies, assigns group keys, and calibrates effort/impact. Then it health-checks everything it just created — descriptions complete, acceptance criteria testable, dependencies acyclic, estimates reasonable.

6. **Read the PM's health report.** Extract:
   - Tasks created (IDs, titles, effort, group)
   - Dependency graph
   - Any health issues found and fixed
   - Anything needing human decision

## Output

Present the plan:

**Design summary** — What the Tech Lead designed. Approach, key decisions, trade-offs. Reference the design doc by title for the user to review in full.

**Task breakdown** — Table of tasks created, with titles, effort, impact, and group. Ordered by dependency (what can start first).

**Dependency graph** — Which tasks block which. Keep it visual if the chain is simple, or describe it if complex.

**Scope estimate** — Total effort across all tasks. Ballpark of how much work this represents.

**Open items** — Anything the PM flagged for human decision, or design questions the TL couldn't resolve.

## Edge Cases

- **Feature overlaps with existing tasks:** The Tech Lead should note overlaps in its decomposition. The PM should avoid creating duplicates. If significant overlap exists, surface it — the user may want to revise existing tasks rather than create new ones.
- **Project has no goal or requirements:** The PM will flag this in its health report. Without clear project-level context, task decomposition may be vague. Suggest the user flesh out the project first or use `/kickoff` to restructure.
- **Decomposition produces too many tasks:** If the Tech Lead produces 15+ tasks for a single feature, that may signal the feature is actually multiple features. Surface this observation and suggest splitting.
