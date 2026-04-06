# Architecture Overview

> **Maintaining this document:** verify against these source files when updating.
>
> - `/.claude-plugin/marketplace.json` -- marketplace registration
> - `/tab/.claude-plugin/plugin.json` -- tab plugin manifest
> - `/tab-for-projects/.claude-plugin/plugin.json` -- tab-for-projects plugin manifest
> - `/tab/settings.json` -- tab default agent setting
> - `/tab-for-projects/settings.json` -- tab-for-projects default agent setting
> - `/tab/agents/tab.md` -- Tab agent definition
> - `/tab-for-projects/agents/manager.md` -- manager agent (orchestration layer)
> - `/tab-for-projects/agents/designer.md` -- designer agent (advisory layer, future-leaning)
> - `/tab-for-projects/agents/tech-lead.md` -- tech lead agent (advisory layer, past-leaning)
> - `/tab-for-projects/agents/planner.md` -- planner agent (advisory layer, task plans)
> - `/tab-for-projects/agents/developer.md` -- developer agent (execution layer)

This repository is a Claude Code plugin marketplace containing two plugins: **tab** and **tab-for-projects**. Both are defined entirely in markdown and JSON -- no compiled code, no runtime dependencies.

---

## Plugin System

Claude Code plugins in this repo follow a three-file structure: a marketplace manifest, per-plugin manifests, and per-plugin settings.

### Marketplace Manifest

`/.claude-plugin/marketplace.json` registers every plugin in the marketplace. It declares the marketplace name, owner, and a `plugins` array where each entry specifies:

| Field | Purpose |
|-------|---------|
| `name` | Plugin identifier (e.g., `tab`, `tab-for-projects`) |
| `source` | Relative path to the plugin root directory |
| `description` | Human-readable summary |
| `version` | Semver version string |
| `strict` | Whether strict mode is enabled |

### Plugin Manifest

Each plugin has its own `.claude-plugin/plugin.json` at its root. This file declares:

| Field | Purpose |
|-------|---------|
| `name` | Plugin name |
| `description` | What the plugin does |
| `version` | Plugin version |
| `author` | Author metadata |
| `license` | License identifier |
| `agents` | Array of relative paths to agent markdown files |
| `skills` | Relative path to the skills directory |

The `agents` array is how Claude Code discovers which agents a plugin provides. The `skills` path points to a directory of skill definitions.

### Settings

Each plugin has a `settings.json` at its root that sets the default agent:

- **tab:** `{ "agent": "tab:Tab" }`
- **tab-for-projects:** `{ "agent": "tab-for-projects:manager" }`

The format is `plugin-name:agent-name`.

---

## tab Package

**Purpose:** Defines the Tab personality -- a thinking partner with configurable personality settings. Tab helps users sharpen ideas, pressure-test plans, and make better decisions.

### Components

| Component | Path | Role |
|-----------|------|------|
| Agent: Tab | `/tab/agents/tab.md` | The sole agent -- defines identity, personality, constraints, and profiles |
| Skill: draw-dino | `/tab/skills/draw-dino` | Skill for drawing a dinosaur |
| Skill: listen | `/tab/skills/listen` | Skill for listening mode |

### Key Concepts

**Personality Settings.** Tab's behavior is governed by five named settings, each weighted 0--100%:

| Setting | What it controls | Default |
|---------|-----------------|---------|
| Humor | Wordplay, clever framing, playful irreverence | 65% |
| Directness | Bluntness vs. diplomacy | 80% |
| Warmth | Friendliness, empathy, reading the room | 70% |
| Autonomy | Asking vs. acting -- how much Tab questions before acting | 50% |
| Verbosity | Response length -- terse to thorough | 35% |

**Profiles.** Named configurations that override specific defaults. Unspecified settings inherit from the base defaults.

| Profile | When it activates | Overrides |
|---------|------------------|-----------|
| Thinking | Problem-solving, brainstorming, decisions | None (home base) |
| Writing | Drafting prose, commit messages, PR descriptions | Humor 35%, Verbosity 25% |
| Technical Docs | API docs, architecture docs, specifications | Humor 15%, Warmth 40%, Verbosity 65%, Directness 90% |
| Teaching | Explaining concepts, onboarding | Warmth 85%, Verbosity 60% |

Tab auto-switches profiles based on context and briefly announces the shift. Users can override profiles or individual settings at any time; overrides persist for the session.

**Constraints.** Three non-negotiable rules:

1. No fabrication -- zero tolerance for unverified factual claims about the codebase.
2. No out-of-scope file access -- only touches files within the user's working directory tree.
3. Guard secrets -- never echoes API keys, tokens, or passwords into conversation.

---

## tab-for-projects Package

**Purpose:** Project management via the Tab for Projects MCP. Provides a conversational interface to track work, capture decisions, and maintain context across sessions.

### Components

| Component | Path | Role |
|-----------|------|------|
| Agent: manager | `/tab-for-projects/agents/manager.md` | Orchestration -- workflows, agent teams, dispatch |
| Agent: designer | `/tab-for-projects/agents/designer.md` | Advisory -- forward-looking design docs, ADRs, architecture |
| Agent: tech-lead | `/tab-for-projects/agents/tech-lead.md` | Advisory -- backward-looking codebase docs, patterns, conventions |
| Agent: planner | `/tab-for-projects/agents/planner.md` | Advisory -- decomposes work into dependency-ordered task graphs |
| Agent: developer | `/tab-for-projects/agents/developer.md` | Execution -- implements tasks, commits from worktrees |
| Skill: mcp-reference | `/tab-for-projects/skills/mcp-reference` | Reference for the Tab for Projects MCP data model and tools |
| Skill: document-reference | `/tab-for-projects/skills/document-reference` | Reference for document types, create-vs-update discipline, tagging |
| Skill: document | `/tab-for-projects/skills/document` | Post-implementation knowledge capture procedure |
| Skill: prompt-reference | `/tab-for-projects/skills/prompt-reference` | Prompt quality conventions and reference |
| Skill: agentic-reference | `/tab-for-projects/skills/agentic-reference` | Conventions for writing Claude Code agents and skills |


### Architecture Pattern: Three-Layer Model

The tab-for-projects agents are organized into three layers: orchestration, advisory, and execution.

```
┌─────────────────────────────────────────────┐
│            ORCHESTRATION                     │
│               Manager                        │
│    (workflows, agent teams, dispatch)         │
├─────────────────────────────────────────────┤
│          ADVISORY (Brain Trust)               │
│                                               │
│    Designer     Tech Lead     Planner         │
│    (future →)   (← past)      (→ tasks)      │
│    writes:      writes:       writes:         │
│    design docs  codebase      task graphs     │
│    ADRs         docs                          │
│    arch docs    patterns                      │
│                 conventions                   │
├─────────────────────────────────────────────┤
│            EXECUTION                          │
│               Developer                       │
│               (code)                          │
└─────────────────────────────────────────────┘
```

**Manager** (`tab-for-projects:manager`): The orchestration layer. Talks to the user and the MCP. Delegates work to advisory agents (individually or as agent teams for complex deliberation) and dispatches developers for implementation. Does not touch the codebase directly.

**Designer** (`tab-for-projects:designer`): Advisory layer, future-leaning. Provides architectural judgment -- elicits requirements, evaluates alternatives, proposes architecture decisions. Writes design docs, ADRs, architecture overviews, and requirements docs. Passes document IDs to teammates. Loads `/document-reference` for document discipline.

**Tech Lead** (`tab-for-projects:tech-lead`): Advisory layer, past-leaning. Provides codebase judgment -- reads code to understand actual patterns, verifies KB docs against codebase reality, flags drift and staleness. Writes and updates codebase pattern records, convention docs, and drift corrections. Handles post-implementation knowledge capture (dispatched with `/document` skill) and KB curation. Loads `/document-reference` for document discipline.

**Planner** (`tab-for-projects:planner`): Advisory layer, task-focused. Reads designer and tech lead documents, explores the codebase, and decomposes scope into dependency-ordered task graphs. Writes tasks with descriptions, plans, acceptance criteria, effort estimates, and dependency edges. Tasks reference advisory documents so developers get the full context chain.

**Developer** (`tab-for-projects:developer`): The execution layer. Receives tasks with plans, gathers context from the document store and codebase, implements the solution, verifies with tests, and commits from worktrees. Benefits from the advisory layer indirectly -- tasks reference accurate KB documents maintained by the designer and tech lead.

### The Three MCP Data Layers

The Tab for Projects MCP organizes data into three layers, each with list/get/create/update operations:

**Projects** -- the top-level container. A project has a title, goal, requirements, and design. These fields capture the strategic context: *why* work is happening.

**Tasks** -- the unit of trackable work. Tasks live inside a project and carry rich fields: title, description, plan, implementation, acceptance_criteria, effort (trivial through extreme), impact (trivial through extreme), category (feature, bugfix, refactor, etc.), group_key (flat grouping label), and status (todo, in_progress, done, archived).

**Documents** -- the knowledgebase layer. Documents are independent top-level entities with a title, content (markdown, up to 100k characters), and tags. They are linked to projects via a many-to-many relationship managed through `update_project` (attach_documents / detach_documents). Documents are designed for agent consumption: architecture decisions, established patterns, gotchas, and integration notes that make future advisory runs more effective. The designer writes forward-looking design docs and ADRs; the tech lead writes backward-looking codebase docs, patterns, and conventions.

---

## How They Relate

**tab** and **tab-for-projects** are separate, independent plugins.

- **tab** is standalone. It defines a personality and thinking style. It requires no external services.
- **tab-for-projects** is an add-on. It provides project management capabilities that depend on the Tab for Projects MCP being connected. It does not depend on or import anything from the tab plugin.

Both plugins are registered in the same marketplace but operate independently. A user can install either or both.

---

## Component Diagram

```
marketplace.json
    |
    +-- tab/
    |     |
    |     +-- plugin.json          (name, agents, skills)
    |     +-- settings.json        (default agent: tab:Tab)
    |     +-- agents/
    |     |     +-- tab.md         (thinking partner agent)
    |     +-- skills/
    |           +-- draw-dino/
    |           +-- listen/
    |           +-- think/
    |           +-- teach/
    |
    +-- tab-for-projects/
          |
          +-- plugin.json          (name, agents, skills)
          +-- settings.json        (default agent: tab-for-projects:manager)
          +-- agents/
          |     +-- manager.md     (orchestration layer)
          |     +-- designer.md    (advisory layer — future-leaning)
          |     +-- tech-lead.md   (advisory layer — past-leaning)
          |     +-- planner.md     (advisory layer — task plans)
          |     +-- developer.md   (execution layer)
          +-- skills/
                +-- mcp-reference/
                +-- document-reference/
                +-- document/
                +-- prompt-reference/
                +-- agentic-reference/

```

### tab-for-projects Internal Architecture

```
+-------------------+
|      User         |
+--------+----------+
         |
         v
+--------+----------+       +---------------------------+
|     Manager       |<----->|   Tab for Projects MCP    |
| (orchestration)   |       |                           |
|                   |       |  +-------+ +------+ +---+ |
| - Conversation    |       |  |Project| | Task | |Doc| |
| - MCP CRUD        |       |  +-------+ +------+ +---+ |
| - Agent teams     |       +---------------------------+
| - Dispatch        |
+--+-----+-----+---+
   |     |     |
   |  advisory layer (brain trust)
   |     |
   v     v
+----------+ +-----------+ +---------+
| Designer | | Tech Lead | | Planner |
|          | |           | |         |
| - Design | | - Read    | | - Read  |
|   docs   | |   code    | |   docs  |
| - ADRs   | | - Update  | | - Write |
| - Arch   | |   docs    | |   tasks |
|   docs   | | - Verify  | | - Plans |
|          | |   KB      | | - Deps  |
+----------+ +-----------+ +---------+
   |
   |  execution layer
   |
   v
+-----------+
| Developer |
|           |
| - Read    |
|   code    |
| - Execute |
|   plans   |
| - Test    |
| - Commit  |
+-----------+
```

---

## Data Flow: tab-for-projects

A typical workflow from user request to completed, documented work:

1. **User talks to the manager.** Describes work they want to track or execute.
2. **Manager creates/updates project-level data** via the MCP (goal, requirements, design).
3. **Manager assembles the advisory brain trust.** For complex work, the manager creates an agent team with the designer, tech lead, and planner (or a subset). For simpler work, it dispatches a single advisory agent directly.
4. **Advisory agents deliberate.** The designer writes design docs and ADRs. The tech lead reads the codebase and writes/updates pattern and convention docs. The planner reads their documents and creates dependency-ordered tasks. All communication uses document IDs as the interface.
5. **Manager dispatches developers** against ready tasks in worktrees. Developers gather context from the task plan and linked KB documents, implement, test, and commit.
6. **Manager dispatches the tech lead** with the `/document` skill for post-implementation knowledge capture. The tech lead reads completed code, compares it to the task plan, and writes/updates documents about what was actually implemented.

```
User --> Manager --> MCP (projects, tasks, documents)
              |
              +--> Designer    --> writes design docs, ADRs (advisory)
              +--> Tech Lead   --> writes/updates codebase docs (advisory)
              +--> Planner     --> writes task graphs (advisory)
              +--> Developer   --> implements tasks, commits (execution)
                                       |
                                       v
                              Tech Lead captures knowledge
                              from completed work via /document
                                       |
                                       v
                              Future advisory runs read these
                              docs as context
```

The knowledge loop is the key architectural insight: the tech lead captures what was learned after implementation, and future advisory runs consume that knowledge to produce better designs, more accurate codebase docs, and more grounded task plans.
