---
name: autopilot
description: "Autonomous project coordination — load the backlog, route tasks to the right agents, build teams, execute work, and drive tasks to completion without checking in at each step."
argument-hint: "[project-name]"
---

# Autopilot

Trigger: ONLY on explicit `/autopilot` invocation. Never auto-trigger. Never infer autopilot intent from user messages. If the user says "just do it" or "handle the backlog," that is NOT an autopilot invocation — ask before running this.

The user is opting out of the conversation loop. They want the system to read the backlog, route tasks to the right agents, build a team, execute, and report — without asking for permission at each step.

## Protocol

### Phase 1: Load State

1. **Resolve the project.** If the user passed an argument, match it against `list_projects`. Otherwise follow standard resolution (check `list_projects`, check `CLAUDE.md`, ask if ambiguous).

2. **Load project context.** Call `get_project` for the goal, requirements, and design.

3. **Build the backlog picture.**

```
get_ready_tasks({ project_id: "..." })      # what's available now
get_dependency_graph({ project_id: "..." })  # what depends on what
list_tasks({ project_id: "...", status: "in_progress" })  # already underway
```

From this, build a mental model:
- **Ready now** — no unfinished blockers, status is `todo`.
- **Blocked** — has dependencies that aren't `done`. Don't touch these.
- **In progress** — already being worked. Don't double-dispatch.

4. **Gather knowledgebase context.** Call `list_documents` for the project. Collect document IDs for relevant conventions, architecture decisions, and prior analysis.

### Phase 2: Route

Read each ready task's `category`, `effort`, `description`, and `plan` to decide which agent type handles it.

| Signal | Routes to | Why |
|--------|-----------|-----|
| category: `feature`, `bugfix`, `refactor`, `chore` with implementation work | **developer** | Code changes needed |
| category: `design` or description indicates architectural decisions | **architect** | System design, not implementation |
| category: `research` or description indicates requirements gaps | **analyst** | Needs elicitation, not execution |
| category: `documentation` or description indicates knowledge capture | **knowledge-writer** | Document store work, not code |

Category alone isn't sufficient. A `feature` task whose plan says "design the API contract" routes to architect, not developer. A `chore` task that says "update the README" routes to knowledge-writer. **Read the task** — don't just pattern-match the category field.

When routing is ambiguous, prefer the agent whose role produces the task's primary artifact: code -> developer, document -> knowledge-writer or architect, structured requirements -> analyst.

**Ceremony scaling.** Effort level determines how much ceremony a task gets:

- **Trivial / Low:** Update status, assign, mark done. No gap analysis. Fast path.
- **Medium:** Check for related documentation. Include relevant context. Verify implementation field on completion.
- **High / Extreme:** Gap analysis first — if a high-effort implementation task has no corresponding test task, create one as a dependency before dispatching. Include relevant document IDs. Verify implementation field describes what changed and why.

**Gap identification.** Before dispatching high-effort tasks, check for missing work:

- **Missing test coverage.** Create a test task and add it as a blocker for the implementation task.
- **Missing design.** A high-effort feature with no architecture context and complex interactions — create a design task routed to architect.
- Only create gap tasks for clear, mechanical gaps. Don't invent speculative work.

**Blocking gaps.** When a task has ambiguous requirements, contradictory constraints, or missing human context — flag it and move on:

```
update_task({ items: [{
  id: "...",
  status: "todo",
  implementation: "BLOCKED: [what's missing and who needs to provide it]"
}] })
```

Do not attempt tasks with unresolvable ambiguity. Continue with other ready work.

### Phase 3: Team Creation

Build the agent team based on routed tasks.

**When to create a team:**
- 2+ independent tasks are ready simultaneously
- Tasks span multiple roles (developer + architect, developer + knowledge-writer)
- Cross-cutting concerns exist where teammates benefit from direct communication

**When individual subagents are better:**
- A single task in isolation — no coordination needed
- Trivial/low effort tasks where team overhead isn't justified
- Tasks that are purely sequential with no parallelism

**Team sizing:**
- Start with 3-5 teammates. More adds coordination overhead with diminishing returns.
- One teammate per independent workstream, not one per task.
- Aim for 5-6 tasks per teammate when batching related work.
- Cap at 5 teammates total.

**File ownership.** For developer teammates, explicitly assign file ownership. Two teammates editing the same file is the primary failure mode. Break work so each developer owns different files.

**Developer teammate brief:**

```
You are a developer teammate working on project [name].

Tasks assigned:
1. [title] (ID: [id], effort: [effort])
   Description: [description]
   Plan: [plan]
   Acceptance criteria: [from description/plan]

Domain context: [frontend/backend/infra/data — conventions and patterns]
Relevant documents: [IDs of attached project docs]
File ownership: [which files/directories this teammate owns]

Follow the developer agent workflow: gather context, implement
(tests first for high effort), verify, commit from the worktree.

When done with each task, message the lead with:
- Task ID
- What changed (files modified, approach taken)
- Any issues discovered that affect other teammates

If you discover something that affects another teammate's work,
message them directly — don't wait for the lead to relay it.
```

**Non-developer teammate brief:**

```
You are the [architect/analyst/knowledge-writer] teammate.

Tasks assigned:
1. [title] (ID: [id])
   Description: [description]
   [Task-specific context and instructions]

When done, message the lead with:
- Task ID
- What you produced
- Any findings that affect other teammates' work
```

**Brief quality rules:**
- **Complete context.** Teammates don't inherit conversation history. Include everything needed.
- **File ownership boundaries.** Explicit for developer teammates.
- **Communication expectations.** When to message each other vs. when to message the lead.
- **No micro-management.** State what needs doing and what constraints apply. Don't prescribe how.

### Phase 4: Execution Management

**Dual task lists.** Two systems are in play — keep them distinct:

| System | Purpose | Authority |
|--------|---------|-----------|
| **MCP task list** | Backlog, dependency graph, status, implementation records | Project state — durable record |
| **Team task list** | In-flight coordination, assignments, blocking/unblocking | Session coordination — ephemeral |

The MCP task list is the authority. When a teammate completes work, update MCP:

```
update_task({ items: [{
  id: "[task-id]",
  status: "done",
  implementation: "[what the teammate reported]"
}] })
```

**Status management:**

| Transition | When |
|-----------|------|
| `todo` -> `in_progress` | Teammate is assigned this task |
| `in_progress` -> `done` | Teammate reports completion (lead updates MCP) |
| remains `todo` | Task is flagged as blocked by a gap |

**Cross-teammate communication.** Teammates message each other directly for:
- API contract discovery — agreeing on interfaces
- Architecture questions — developer asks architect instead of waiting for the lead
- Documentation gaps — architect flags something for knowledge-writer
- Conflict detection — overlapping file ownership

**When to intervene as lead:**
- A teammate is idle or stuck for too long — send guidance or reassign
- Cross-teammate communication has stalled — mediate
- A teammate is working outside its file ownership without coordination
- New tasks become ready (blockers completed) — assign to available teammates

**Backlog refresh.** After tasks complete, check if previously blocked tasks are now ready. Assign new work to available teammates or spawn additional ones.

### Phase 5: Completion

1. **Clean up the team.** When no more work remains, shut down all teammates.
2. **Update MCP status.** Ensure every completed task has its MCP status and implementation field updated.
3. **Report.** Present to the user:
   - Tasks completed — what was done and by whom
   - Tasks flagged — blocked gaps, ambiguous requirements
   - Gap tasks created — test coverage, design tasks
   - Tasks still blocked or in progress
   - Items that need the user's judgment
4. **Stop when done.** When no ready tasks remain (all done, all blocked, or all flagged), the run is complete. Don't loop indefinitely.

## Constraints

- **Don't implement directly.** Autopilot reads task state, routes work, and manages the team. It never touches the codebase.
- **Don't author documents.** Route document tasks to knowledge-writer or architect teammates.
- **Never commit code.** The developer teammate owns commits. Autopilot owns task state.
- **Respect the dependency graph.** Never assign a task whose blockers aren't `done`. No exceptions.
- **Don't over-create.** Gap tasks are for clear mechanical gaps (missing tests, missing design). Don't invent speculative work.
- **Avoid file conflicts.** The most important team creation decision. Each developer teammate owns different files.
- **MCP is the authority.** The team task list coordinates in-session. The MCP task list is the durable project record. Always update MCP on completion.
- **Flag ambiguous tasks.** If a task can't be routed or has unresolvable ambiguity, flag it and skip it — don't guess.
- **Cap at 5 teammates.** More adds coordination overhead without proportional throughput gain.
