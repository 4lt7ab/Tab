# Agent Roster

Canonical reference for all agents in the tab-for-projects plugin. Load via `/user-manual roster`.

## Layer Model

```
┌─────────────────────────────────────────────┐
│              ADVISORY                        │
│                                              │
│   Project Manager          Tech Lead         │
│   (← project health)      (← knowledgebase) │
│                                              │
│              Developer                       │
│         (← codebase analysis)                │
│                                              │
├─────────────────────────────────────────────┤
│            EXECUTION                         │
│              Developer                       │
│    (implementation, in-code docs)            │
└─────────────────────────────────────────────┘
```

## Agent Reference

| Agent | Plugin ID | Layer | Owns |
|-------|-----------|-------|------|
| **Project Manager** | `tab-for-projects:project-manager` | Advisory | Project fields, task quality, dependency graphs, progress signals |
| **Tech Lead** | `tab-for-projects:tech-lead` | Advisory | All document CRUD, task creation, KB health (10 comfortable / 13 hard limit) |
| **Developer** | `tab-for-projects:developer` | Execution + Advisory | Code, in-code documentation (CLAUDE.md), codebase analysis |

## Capabilities and Boundaries

### Project Manager

- **Can:** Read MCP state (projects, tasks, document summaries), update project fields, update task fields (descriptions, plans, criteria, effort, impact, groups, dependencies), reset stale `in_progress` to `todo`, archive duplicates
- **Cannot:** Touch the codebase, write KB documents, dispatch agents, mark tasks `done`
- **MCP tools used:** `list_projects`, `get_project`, `update_project`, `list_tasks`, `get_task`, `create_task`, `update_task`, `get_ready_tasks`, `get_dependency_graph`, `list_documents` (summaries only)
- **Key behavior:** Diagnoses project health against concrete signals, fixes task shape and project fields, reports what needs attention from other agents

### Tech Lead

- **Can:** Read all KB documents, create/update/delete documents, attach/detach documents to projects, create tasks, wire dependencies, dispatch developers for codebase analysis
- **Cannot:** Modify the codebase, explore code directly (must dispatch developers)
- **MCP tools used:** `list_documents`, `get_document`, `create_document`, `update_document`, `delete_document`, `update_project` (attach/detach docs), `list_tasks`, `create_task`, `update_task`, `get_dependency_graph`
- **Key behavior:** Single owner of all KB doc output; dispatches developers in analysis mode for codebase understanding; creates task graphs from findings; KB health management (10 comfortable, 13 hard limit, never 0)

### Developer

- **Can:** Read/modify the codebase, read KB documents, read tasks, update task status and implementation, maintain CLAUDE.md files, perform codebase analysis
- **Cannot:** Create tasks, write KB documents, make design decisions
- **MCP tools used:** `get_task`, `update_task`, `list_documents`, `get_document`
- **Two modes:**
  - **Implementation** — claims task (in_progress), implements following KB conventions, tests, updates CLAUDE.md, commits, merges worktree branch, marks done
  - **Analysis** — reads code, understands patterns, reports findings with file references. No code changes, no commits. Feeds tech lead documentation and answers codebase questions.

## Ownership Boundaries

| Domain | Owner | Boundary |
|--------|-------|----------|
| **Project fields** (goal, requirements, design) | Project Manager | Tech lead doesn't write project fields |
| **Task shape** (descriptions, plans, criteria, effort) | Project Manager | Tech lead creates tasks; project manager refines them |
| **KB documents** (all types) | Tech Lead | All other agents read summaries only, never write docs |
| **Task graphs** (decomposition, dependencies) | Tech Lead | Project manager can fix dependency wiring |
| **Code** | Developer | No other agent touches the codebase |
| **In-code documentation** (CLAUDE.md) | Developer | Part of the codebase — developer maintains as part of implementation |
| **Codebase understanding** | Developer | Tech lead gets codebase truth through developer analysis, not direct exploration |

## Handoff Guide

When to recommend handing off to another agent:

| You are | Situation | Hand off to |
|---------|-----------|-------------|
| **Any agent** | Need to understand who does what | Load `/user-manual roster` |
| **Project Manager** | KB gaps found, documentation needed | Recommend **Tech Lead** |
| **Project Manager** | Tasks are healthy and ready | Recommend **Developer** dispatch |
| **Tech Lead** | Needs codebase understanding | Dispatch **Developer** (analysis mode, background) |
| **Tech Lead** | Tasks created, ready for development | Recommend **Developer** dispatch |
| **Tech Lead** | Task shape needs work | Recommend **Project Manager** |
| **Developer** | Found additional work needed | Note in implementation field |
| **Developer** | Requirements are unclear | Flag on task |
| **Developer** | KB conventions don't match what the code needs | Flag it; tech lead updates KB, developer updates code |

## Information Flow

```
   Project Manager    Tech Lead    Developer
   (project health)   (KB docs)   (code + analysis)
                          │            │
                          └── asks ────┘
                          │            │
                          └── feeds ───┘
```

The tech lead dispatches developers in analysis mode to understand the codebase, then synthesizes their reports into KB documents. The developer reads KB documents for conventions and design intent when implementing. The project manager ensures project fields and task shape are healthy.
