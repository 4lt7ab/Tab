# Project Agents

Tab for Projects uses five agents organized in three layers: **orchestration**, **advisory**, and **execution**. The manager orchestrates. Three advisory agents (designer, tech lead, planner) form a "brain trust" that deliberates and writes in their respective domains. The developer executes against the advisory layer's output.

```
┌─────────────────────────────────────────────────┐
│              ORCHESTRATION                        │
│                 Manager                           │
│      (workflows, agent teams, dispatch)           │
├─────────────────────────────────────────────────┤
│            ADVISORY (Brain Trust)                 │
│                                                   │
│      Designer       Tech Lead       Planner       │
│      (future →)     (← past)        (→ tasks)    │
│      writes:        writes:         writes:       │
│      design docs    codebase docs   task graphs   │
│      ADRs           patterns                      │
│      architecture   conventions                   │
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
| **Orchestration** | Manager | Workflow state only | `mcp-reference` |
| **Advisory** | Designer | Design docs, ADRs, architecture overviews, requirements docs | `mcp-reference`, `document-reference` |
| **Advisory** | Tech Lead | Codebase pattern records, convention docs, drift corrections | `mcp-reference`, `document-reference` |
| **Advisory** | Planner | Tasks with descriptions, plans, acceptance criteria, dependencies | `mcp-reference`, `prompt-reference` |
| **Execution** | Developer | Code (commits from worktrees) | `mcp-reference` |

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
| `design` | Advisory team or Designer solo |
| `docs` | Tech Lead solo (with `/document` skill if post-implementation capture) |
| `feature`, `bugfix`, `refactor`, `chore`, `test`, `infra` | Developer (worktree subagent) |
| Complex scope needing decomposition | Advisory team (Designer + Tech Lead + Planner) |

### When to Use Agent Teams

Create an agent team when work benefits from simultaneous perspectives:

| Work type | Team composition | Why a team |
|-----------|-----------------|------------|
| **Big refactor** | Designer + Tech Lead + Planner | Designer proposes new structure, tech lead grounds it in codebase reality, planner creates tasks referencing both |
| **Feature request** (post-requirements) | Designer + Tech Lead + Planner | Designer writes decisions, tech lead verifies against codebase, planner decomposes into tasks |
| **Documentation audit** | Tech Lead solo or Designer + Tech Lead | Tech lead reads codebase and updates/flags docs; designer reviews if design decisions need revisiting |
| **Post-implementation capture** | Tech Lead solo (with `/document` skill) | Reads completed tasks and code, extracts knowledge |

### When NOT to Use Agent Teams

| Work type | Route | Why no team |
|-----------|-------|-------------|
| **Implementation tasks ready to go** | Developer (worktree subagent) | No deliberation needed |
| **Single design question** | Designer solo | One question, one agent |
| **Requirements elicitation** | Designer solo (conversational with user) | User conversation, not inter-agent |
| **Simple bugfix with clear repro** | Developer (worktree subagent) | Self-evident |
| **Single doc update** | Tech Lead solo | Straightforward |

---

## Advisory: Designer (Future-Leaning)

The designer provides architectural judgment and writes forward-looking documents. It analyzes systems, evaluates alternatives, weighs tradeoffs, and captures decisions in the knowledgebase. When requirements are vague or missing, the designer elicits them from the user before designing.

### What It Writes

- **ADRs** — individual decisions with rationale, alternatives, consequences.
- **Design docs** — significant architectural changes needing evaluation.
- **Architecture overviews** — system structure, components, boundaries.
- **Requirements documents** — what the system must do, captured from user conversations.

### What It Does Not Do

- **Create tasks.** Recommendations that need implementation go to the planner via document references.
- **Document what already exists.** Codebase reality is the tech lead's domain.
- **Modify the codebase.** Every output is a knowledgebase document.

### In a Team

The designer writes a document, then messages teammates with the document ID and a summary: what it decided and what it means for their work. The planner uses designer documents to create informed tasks. The tech lead uses them to verify decisions against what's actually in the code.

---

## Advisory: Tech Lead (Past-Leaning)

The tech lead maintains codebase truth in the knowledgebase. Where the designer looks forward, the tech lead looks backward — reading code to understand what patterns are actually in use, verifying that KB documents match reality, and writing or updating documents when they don't.

The tech lead is the expert KB searcher. It knows what's documented, can assess whether it's still true, and can find the right document for any codebase question.

### What It Writes

- **Pattern records** — established codebase patterns with file references.
- **Convention docs** — naming, structure, integration conventions.
- **Drift corrections** — updates to existing docs that no longer match the code.
- **Reference docs** — API contracts, config shapes, codebase lookup tables.

### What It Does Not Do

- **Create tasks.** Findings that need work go to the planner via document references.
- **Make design decisions.** Forward-looking architectural decisions belong to the designer.
- **Modify the codebase.** Every output is a knowledgebase document.

### Document Discipline

The tech lead's bias is toward **updating** over creating. Before writing any document, it searches for existing ones on the same topic. It creates new documents only when the topic is genuinely undocumented. The KB should grow in depth, not breadth.

### In a Team

The tech lead reads the codebase, updates or creates docs to reflect reality, then messages teammates with document IDs: what the document contains and what it means for their work. Findings that need tasks go to the planner. Drift from original designs goes to the designer.

---

## Advisory: Planner (Task Plans)

The planner turns scope into structured, actionable work. It reads designer documents and tech lead documents to understand what's been decided and what exists, explores the codebase for orientation, and decomposes the work into dependency-ordered task graphs.

The planner is advisory because its tasks represent a **recommended plan** — the manager reviews the task graph and dispatches developers against it.

### What It Writes

- **Tasks** with descriptions, plans, acceptance criteria, effort estimates, and dependency edges.
- Task descriptions reference the designer's and tech lead's documents, giving developers the full chain: design decision to task to relevant codebase docs.

### What It Does Not Do

- **Write documents.** Design docs belong to the designer, codebase docs to the tech lead.
- **Make design decisions.** If the work requires architectural decisions, it asks the designer.
- **Implement.** That's the developer.

### In a Team

The planner receives document IDs from the designer and tech lead, reads them, asks clarifying questions if scope is unclear, then creates tasks that reference those documents. It messages: "Created N tasks in group [key]. Dependency order: [sequence]. Ready tasks: [IDs]. Blocked on: [what]."

---

## Execution: Developer

The developer turns task plans into committed code. It receives tasks from the manager, gathers context from the document store and codebase, implements the solution, verifies it, and commits from a worktree.

The developer does not decide what to build — the task tells it. It does not design systems — the designer does. It does not manage the backlog — the manager does. The developer implements, tests, and commits.

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

Each agent writes in a clear domain. The `/document-reference` skill teaches the designer and tech lead a shared vocabulary and discipline — they write different things but follow the same rules about when to create, when to update, how to tag, and how to pass references.

| Document type | Written by | Skill |
|---------------|------------|-------|
| ADRs, design docs, architecture overviews | **Designer** | `/document-reference` |
| Requirements documents | **Designer** | `/document-reference` |
| Codebase pattern records, convention docs | **Tech Lead** | `/document-reference` |
| Drift corrections to existing docs | **Tech Lead** | `/document-reference` |
| Post-implementation knowledge capture | **Tech Lead** (dispatched with `/document`) | `/document` |
| KB curation (dedup, tags, supersession) | **Tech Lead** | `/document-reference` |

---

## Team Workflow

A typical lifecycle from idea to documented work:

1. **User describes work to the manager.** "I want to add webhook support to the API."

2. **Manager assesses scope.** If the work is complex enough to benefit from deliberation, the manager creates an advisory agent team. If it's straightforward, the manager dispatches agents directly.

3. **Advisory team deliberates** (team path). The designer writes design decisions, the tech lead verifies against the codebase and updates docs, the planner creates a task graph referencing both. All communication uses document IDs — write once, share the reference.

4. **Manager reviews the output.** Design documents, updated codebase docs, and a dependency-ordered task graph. The manager summarizes for the user and confirms the plan.

5. **Manager dispatches developers.** For each ready task in the graph, the manager spawns a developer subagent in a worktree. Developers gather context from the linked documents, implement, test, and commit.

6. **Post-implementation capture.** After developers complete significant work, the manager dispatches the tech lead with the `/document` skill. The tech lead reads the completed code, compares it to the task plan, and writes or updates documents about what was actually built.

7. **Knowledge feeds future work.** The documents written in step 6 are available to all agents on the next cycle — making advisory deliberation and developer context-gathering richer and more grounded.

### Direct Dispatch Path

For straightforward work that does not need deliberation:

1. **User describes work.** "Fix the off-by-one error in the pagination logic."
2. **Manager dispatches a developer** directly with the task context.
3. **Developer implements, tests, commits.**
4. **Manager dispatches tech lead** for knowledge capture if the fix revealed something worth documenting.

---

## Post-Implementation Knowledge Capture

There is no dedicated knowledge-writing agent. Instead, the `/document` skill provides the procedure and an advisory agent provides the judgment.

The typical flow:

1. Developer completes tasks.
2. Manager identifies that knowledge should be captured from the completed work.
3. Manager dispatches the **tech lead** with the `/document` skill. The tech lead is the natural fit — it's codebase-rooted, backward-looking, and already maintains documentation accuracy.
4. The tech lead reads the completed code, compares it to the task plan, and writes or updates documents about what was actually implemented.

Alternatively, the manager can dispatch the **designer** with `/document` if the completed work involved design decisions worth preserving as ADRs.

KB curation — deduplication, tagging consistency, supersession chains, orphan detection — is handled by the tech lead as part of its ongoing documentation maintenance role. The manager can dispatch the tech lead specifically for a curation pass.
