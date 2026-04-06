# Agent Roster

Canonical reference for all agents in the tab-for-projects plugin. Load via `/user-manual roster`.

## Three-Layer Model

```
┌─────────────────────────────────────────────┐
│            ORCHESTRATION                     │
│               Manager                        │
├─────────────────────────────────────────────┤
│          ADVISORY (Brain Trust)               │
│         Tech Lead          Planner            │
├─────────────────────────────────────────────┤
│            EXECUTION                          │
│               Developer                       │
└─────────────────────────────────────────────┘
```

## Agent Reference

| Agent | Plugin ID | Layer | Role | Produces | Owns |
|-------|-----------|-------|------|----------|------|
| **Manager** | `tab-for-projects:manager` | Orchestration | Routes work to agents, creates teams, tracks progress | Workflow state, dispatch briefs | Project lifecycle, agent coordination |
| **Tech Lead** | `tab-for-projects:tech-lead` | Advisory | Writes all KB documents, maintains codebase truth, manages KB health | All KB documents (design docs, ADRs, codebase docs, pattern records, convention docs) | All document CRUD, KB health (10-doc soft cap) |
| **Planner** | `tab-for-projects:planner` | Advisory | Decomposes scope into tasks, wires dependencies | Tasks with descriptions, plans, acceptance criteria, dependency graphs | Task creation and dependency ordering |
| **Developer** | `tab-for-projects:developer` | Execution | Implements tasks, writes tests, commits code | Code commits from worktrees, task status updates | Implementation, testing, commits, merges |

## Capabilities and Boundaries

### Manager

- **Can:** Read MCP state (projects, tasks, document summaries), spawn agents, create agent teams, update project fields, create tasks
- **Cannot:** Touch the codebase, fetch full document content, mark tasks done, do substantive work
- **MCP tools used:** All project/task/document list/get tools, Agent tool
- **Dispatch modes:** Agent teams (complex work), direct dispatch (focused work)

### Tech Lead

- **Can:** Read code (via subagents), read all KB documents, create/update/delete documents, attach/detach documents to projects
- **Cannot:** Modify the codebase, create tasks
- **MCP tools used:** `list_documents`, `get_document`, `create_document`, `update_document`, `delete_document`, `update_project` (attach/detach docs), `list_tasks`
- **Key behavior:** Single owner of all doc output; KB health management with 10-doc soft cap; writes all design docs and codebase docs

### Planner

- **Can:** Read code (via subagents), read KB documents, create tasks, wire dependencies
- **Cannot:** Modify the codebase, write documents, make design decisions
- **MCP tools used:** `get_project`, `list_tasks`, `create_task`, `update_task`, `list_documents`, `get_document`, `get_dependency_graph`
- **Key behavior:** Decomposes scope into one-agent-session tasks; each task targets one role

### Developer

- **Can:** Read/modify the codebase, read KB documents, read tasks, update task status and implementation
- **Cannot:** Create tasks, write documents, make design decisions
- **MCP tools used:** `get_task`, `update_task`, `list_documents`, `get_document`
- **Key behavior:** Claims task (in_progress), implements, tests, commits, merges worktree branch, marks done

## Handoff Guide

When to recommend handing off to another agent:

| You are | Situation | Hand off to |
|---------|-----------|-------------|
| **Any agent** | Need to understand who does what | Load `/user-manual roster` |
| **Manager** | Design decisions needed or documents need writing | **Tech Lead** (solo or in advisory team) |
| **Manager** | Tasks need creating from existing design | **Planner** |
| **Manager** | Tasks are ready for implementation | **Developer** (worktree) |
| **Tech Lead** | Found issues needing tasks | **Planner** (via document references) |
| **Planner** | Requirements are ambiguous | Flag for **Manager** to resolve |
| **Planner** | Design is missing for scope | **Tech Lead** (design needed) |
| **Developer** | Found additional work needed | Note in implementation field; **Manager** routes to planner |
| **Developer** | Requirements are unclear | Flag on task; **Manager** resolves |

## Document Flow

```
Tech Lead ──KB documents──> Planner ──tasks──> Developer
    │                                              │
    └──────────── codebase docs <── reads code ────┘
```

The tech lead is the single funnel for all document output. Design decisions and codebase truth both flow through the tech lead into the KB. The planner and developer read documents but never write them.
