# Project Agents

Tab for Projects uses four agents organized in three layers: **orchestration**, **advisory**, and **execution**. The manager orchestrates. Two advisory agents (tech lead, planner) form a "brain trust" that deliberates and writes in their respective domains. The developer executes against the advisory layer's output.

```
┌─────────────────────────────────────────────────┐
│              ORCHESTRATION                        │
│                 Manager                           │
│      (workflows, agent teams, dispatch)           │
├─────────────────────────────────────────────────┤
│            ADVISORY (Brain Trust)                 │
│                                                   │
│            Tech Lead          Planner             │
│            (← all docs)      (→ tasks)            │
│            writes:           writes:              │
│            all KB docs       task graphs          │
│            (design + codebase)                    │
├─────────────────────────────────────────────────┤
│              EXECUTION                            │
│                 Developer                         │
│                  (code)                            │
└─────────────────────────────────────────────────┘
```

The key separation: advisory agents exercise **judgment** (what should we do? what exists? what order?) and produce **documents and tasks**. The execution agent produces **code**. The manager sets up the right agents for the work and dispatches them — it does not join deliberation.

All persistent state lives in the MCP. Communication between advisory agents uses document IDs, not text blobs — write the document, share the ID.

---

## Layer Summary

| Layer | Agent | Writes | Loaded Skills |
|-------|-------|--------|---------------|
| **Orchestration** | Manager | Workflow state only | `user-manual` |
| **Advisory** | Tech Lead | All KB documents (design docs, ADRs, codebase pattern records, convention docs, drift corrections) | `user-manual` |
| **Advisory** | Planner | Tasks with descriptions, plans, acceptance criteria, dependencies | `user-manual` |
| **Execution** | Developer | Code (commits from worktrees) | `user-manual` |

---

## Orchestration: Manager

The manager is a dispatch agent. It reads project state from the MCP, assesses what kind of work is needed, and routes it to the right agents. It operates in two modes:

| Mode | When | How |
|------|------|-----|
| **Agent team** | Complex work needing multi-perspective deliberation | Creates a Claude Code agent team from the advisory layer |
| **Direct dispatch** | Straightforward, single-agent work | Spawns a subagent |

### The Hard Rule

The manager does exactly two things:

1. **Talks to the user** — conversation, decisions, context capture.
2. **Talks to the MCP** — CRUD on projects, tasks, and documents.

It never touches the codebase. It never fetches full document content into the main thread. It never marks tasks done — agents own their own status transitions. When work requires reading code, exploring the codebase, or making changes, the manager dispatches an agent.

### Routing

On start, the manager loads project state and routes existing work:

| Task category | Route to |
|---------------|----------|
| `design` | Advisory team or Tech Lead solo |
| `docs` | Tech Lead solo |
| `feature`, `bugfix`, `refactor`, `chore`, `test`, `infra` | Developer (worktree subagent) |
| Complex scope needing decomposition | Advisory team (Tech Lead + Planner) |

### When to Use Agent Teams

Create an agent team when work benefits from simultaneous perspectives:

| Work type | Team composition | Why a team |
|-----------|-----------------|------------|
| **Big refactor** | Tech Lead + Planner | Tech lead assesses codebase reality and writes docs, planner creates tasks referencing them |
| **Feature request** (post-requirements) | Tech Lead + Planner | Tech lead writes design and codebase docs, planner decomposes into tasks |
| **Documentation audit** | Tech Lead solo | Tech lead reads codebase and updates/flags docs |
| **Post-implementation capture** | Tech Lead solo | Reads completed tasks and code, extracts knowledge |

### When NOT to Use Agent Teams

| Work type | Route | Why no team |
|-----------|-------|-------------|
| **Implementation tasks ready to go** | Developer (worktree subagent) | No deliberation needed |
| **Single design question** | Tech Lead solo | One question, one agent |
| **Simple bugfix with clear repro** | Developer (worktree subagent) | Self-evident |
| **Single doc update** | Tech Lead solo | Straightforward |

---

## Advisory: Tech Lead

The tech lead is the single owner of all knowledgebase documents. It writes design docs, ADRs, and architecture overviews alongside codebase pattern records, convention docs, and drift corrections. It reads code to understand what patterns are actually in use, verifies that KB documents match reality, and writes or updates documents when they don't.

The tech lead is the expert KB searcher. It knows what's documented, can assess whether it's still true, and can find the right document for any codebase question.

### What It Writes

- **Design docs** — significant architectural changes needing evaluation.
- **ADRs** — individual decisions with rationale, alternatives, consequences.
- **Architecture overviews** — system structure, components, boundaries.
- **Pattern records** — established codebase patterns with file references.
- **Convention docs** — naming, structure, integration conventions.
- **Drift corrections** — updates to existing docs that no longer match the code.
- **Reference docs** — API contracts, config shapes, codebase lookup tables.

### What It Does Not Do

- **Create tasks.** Findings that need work go to the planner via document references.
- **Modify the codebase.** Every output is a knowledgebase document.

### Document Discipline

The tech lead's bias is toward **updating** over creating. Before writing any document, it searches for existing ones on the same topic. It creates new documents only when the topic is genuinely undocumented. The KB should grow in depth, not breadth.

### In a Team

The tech lead reads the codebase, updates or creates docs to reflect reality, then messages teammates with document IDs: what the document contains and what it means for their work. Findings that need tasks go to the planner.

---

## Advisory: Planner (Task Plans)

The planner turns scope into structured, actionable work. It reads tech lead documents to understand what's been decided and what exists, explores the codebase for orientation, and decomposes the work into dependency-ordered task graphs.

The planner is advisory because its tasks represent a **recommended plan** — the manager reviews the task graph and dispatches developers against it.

### What It Writes

- **Tasks** with descriptions, plans, acceptance criteria, effort estimates, and dependency edges.
- Task descriptions reference the tech lead's documents, giving developers the full chain: design decision to task to relevant codebase docs.

### What It Does Not Do

- **Write documents.** All documents belong to the tech lead.
- **Implement.** That's the developer.

### In a Team

The planner receives document IDs from the tech lead, reads them, asks clarifying questions if scope is unclear, then creates tasks that reference those documents. It messages: "Created N tasks in group [key]. Dependency order: [sequence]. Ready tasks: [IDs]. Blocked on: [what]."

---

## Execution: Developer

The developer turns task plans into committed code. It receives tasks from the manager, gathers context from the document store and codebase, implements the solution, verifies it, and commits from a worktree.

The developer does not decide what to build — the task tells it. It does not manage the backlog — the manager does. The developer implements, tests, and commits.

### What It Does

1. **Gathers context** — reads the task plan, searches the document store for relevant conventions and architecture decisions, explores the codebase to understand existing patterns.
2. **Implements** — writes the code. Tests first for non-trivial work. Follows existing patterns and conventions.
3. **Verifies** — runs tests, checks that acceptance criteria are met.
4. **Commits** — creates a meaningful commit from the worktree, then merges back.

### What It Does Not Do

- **Create tasks.** If it discovers additional work needed, it notes it in the task's implementation field.
- **Write documents.** Post-implementation knowledge capture is dispatched separately.
- **Expand scope.** Adjacent improvements are noted, not applied.

---

## Document Ownership

The tech lead is the single owner of all KB document output. The `/user-manual documents` reference teaches the document discipline — when to create, when to update, how to tag, and how to pass references.

| Document type | Written by | Reference |
|---------------|------------|-----------|
| ADRs, design docs, architecture overviews | **Tech Lead** | `/user-manual documents` |
| Codebase pattern records, convention docs | **Tech Lead** | `/user-manual documents` |
| Drift corrections to existing docs | **Tech Lead** | `/user-manual documents` |
| Post-implementation knowledge capture | **Tech Lead** | `/user-manual documents` |
| KB curation (dedup, tags, supersession) | **Tech Lead** | `/user-manual documents` |

---

## Team Workflow

A typical lifecycle from idea to documented work:

1. **User describes work to the manager.** "I want to add webhook support to the API."

2. **Manager assesses scope.** If the work is complex enough to benefit from deliberation, the manager creates an advisory agent team. If it's straightforward, the manager dispatches agents directly.

3. **Advisory team deliberates** (team path). The tech lead writes design decisions and verifies against the codebase, the planner creates a task graph referencing the documents. All communication uses document IDs — write once, share the reference.

4. **Manager reviews the output.** Design documents, updated codebase docs, and a dependency-ordered task graph. The manager summarizes for the user and confirms the plan.

5. **Manager dispatches developers.** For each ready task in the graph, the manager spawns a developer subagent in a worktree. Developers gather context from the linked documents, implement, test, and commit.

6. **Post-implementation capture.** After developers complete significant work, the manager dispatches the tech lead. The tech lead reads the completed code, compares it to the task plan, and writes or updates documents about what was actually built.

7. **Knowledge feeds future work.** The documents written in step 6 are available to all agents on the next cycle — making advisory deliberation and developer context-gathering richer and more grounded.

### Direct Dispatch Path

For straightforward work that does not need deliberation:

1. **User describes work.** "Fix the off-by-one error in the pagination logic."
2. **Manager dispatches a developer** directly with the task context.
3. **Developer implements, tests, commits.**
4. **Manager dispatches tech lead** for knowledge capture if the fix revealed something worth documenting.

---

## Post-Implementation Knowledge Capture

There is no dedicated knowledge-writing agent. The tech lead handles post-implementation capture as part of its core role — it's codebase-rooted, backward-looking, and already maintains documentation accuracy.

The typical flow:

1. Developer completes tasks.
2. Manager identifies that knowledge should be captured from the completed work.
3. Manager dispatches the **tech lead**. The tech lead reads the completed code, compares it to the task plan, and writes or updates documents about what was actually implemented.

KB curation — deduplication, tagging consistency, supersession chains, orphan detection — is handled by the tech lead as part of its ongoing documentation maintenance role. The manager can dispatch the tech lead specifically for a curation pass.
