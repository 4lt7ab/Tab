# Architecture Overview

> **Maintaining this document:** verify against these source files when updating.
>
> - `/.claude-plugin/marketplace.json` -- marketplace registration
> - `/tab/.claude-plugin/plugin.json` -- tab plugin manifest
> - `/tab-for-projects/.claude-plugin/plugin.json` -- tab-for-projects plugin manifest
> - `/tab/settings.json` -- tab default agent setting
> - `/tab/agents/tab.md` -- Tab agent definition
> - `/tab-for-projects/agents/manager.md` -- manager agent (entry point, subagent protocol)
> - `/tab-for-projects/agents/planner.md` -- planner subagent
> - `/tab-for-projects/agents/qa.md` -- QA subagent
> - `/tab-for-projects/agents/documenter.md` -- documenter subagent
> - `/tab-for-projects/agents/coordinator.md` -- coordinator subagent
> - `/tab-for-projects/agents/bugfixer.md` -- bugfixer subagent (foreground)
> - `/tab-for-projects/agents/implementer.md` -- implementer subagent

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

The `tab` plugin has a `settings.json` at its root that sets the default agent:

- **tab:** `{ "agent": "tab:Tab" }`

The format is `plugin-name:agent-name`. The `tab-for-projects` plugin does not have a `settings.json`.

---

## tab Package

**Purpose:** Defines the Tab personality -- a thinking partner with configurable personality settings. Tab helps users sharpen ideas, pressure-test plans, and make better decisions.

### Components

| Component | Path | Role |
|-----------|------|------|
| Agent: Tab | `/tab/agents/tab.md` | The sole agent -- defines identity, personality, constraints, and profiles |
| Skill: draw-dino | `/tab/skills/draw-dino` | Skill for drawing a dinosaur |
| Skill: listen | `/tab/skills/listen` | Skill for listening mode |
| Skill: teach | `/tab/skills/teach` | Interactive teaching sessions |
| Skill: think | `/tab/skills/think` | Conversational idea capture |

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
| Agent: manager | `/tab-for-projects/agents/manager.md` | Entry point -- talks to the user and the MCP, delegates codebase work |
| Agent: planner | `/tab-for-projects/agents/planner.md` | Background subagent -- decomposes work into tasks with plans and acceptance criteria |
| Agent: qa | `/tab-for-projects/agents/qa.md` | Background subagent -- validates work against plans, finds gaps, creates findings |
| Agent: documenter | `/tab-for-projects/agents/documenter.md` | Background subagent -- captures knowledge from completed work into MCP documents |
| Agent: coordinator | `/tab-for-projects/agents/coordinator.md` | Background subagent -- assesses project health, produces reports or dispatch instructions |
| Agent: bugfixer | `/tab-for-projects/agents/bugfixer.md` | Foreground subagent -- pair-programs with the user to hunt and fix bugs |
| Agent: implementer | `/tab-for-projects/agents/implementer.md` | Background subagent -- executes task plans, self-validates against acceptance criteria |
| Skill: design | `/tab-for-projects/skills/design` | Feature design and task decomposition |
| Skill: develop | `/tab-for-projects/skills/develop` | Working session orchestration |
| Skill: retro | `/tab-for-projects/skills/retro` | Conversation-to-task extraction |

### Architecture Pattern: Manager Delegates to Subagents

The manager agent is the only agent that talks to the user. It enforces a strict separation:

- **Manager** handles conversation and MCP operations (CRUD on projects, tasks, documents).
- **Subagents** handle all codebase work (reading files, searching, running commands).

Most subagents run in the background (`run_in_background: true`) so the main conversation thread is never blocked. The one exception is the bugfixer, which runs in the foreground and talks directly to the user. The manager spawns subagents with scoped prompts containing the relevant project context, task IDs, and knowledgebase document IDs. When a background subagent completes, the manager summarizes the result for the user.

The six named subagents and their responsibilities:

**Planner** (`tab-for-projects:planner`): Receives a work description or existing task IDs. Researches the codebase to ground its understanding, breaks work into right-sized tasks, writes implementation plans and acceptance criteria, and writes everything to the MCP via `create_task` or `update_task`.

**QA** (`tab-for-projects:qa`): Receives a validation scope (specific task IDs, a group key, or "full" for the entire project). Inspects both MCP records and the actual codebase. Reaches a verdict per task (pass, pass-with-notes, fail-with-reasons). Creates new tasks with `group_key: "qa-findings"` for any gaps discovered, and resets failed tasks to `todo` status.

**Documenter** (`tab-for-projects:documenter`): Receives completed task IDs. Reads the tasks and the actual codebase, extracts architectural decisions, patterns, and gotchas, then writes them into MCP knowledgebase documents. Updates existing documents when possible to avoid duplication. Attaches new documents to the project via `update_project`.

**Coordinator** (`tab-for-projects:coordinator`): Receives a project ID, scope, and mode (report or coordinate). Reads the full project state — knowledgebase, backlog, goals — and synthesizes it into either a structured assessment (report mode) or a combination of direct MCP actions and dispatch instructions for specialist agents (coordinate mode). Does not touch the codebase; operates purely on MCP data.

**Bugfixer** (`tab-for-projects:bugfixer`): Runs in the **foreground** (`run_in_background: false`) — the only subagent that talks directly to the user. Pair-programs to hunt and fix bugs in real time. Reads code, runs tests, writes fixes, and tracks findings in the MCP. Spawned via the `/bugfix` skill.

**Implementer** (`tab-for-projects:implementer`): Receives task IDs with existing plans. Verifies plan assumptions against the current codebase, executes the plan, self-validates against acceptance criteria, and updates task status and implementation fields in the MCP. Does not write plans — if a task has no plan, it flags it and skips it.

The manager can also spawn **ad-hoc subagents** for generic codebase work that does not fit the named roles.

### The Three MCP Data Layers

The Tab for Projects MCP organizes data into three layers, each with list/get/create/update operations:

**Projects** -- the top-level container. A project has a title, goal, requirements, and design. These fields capture the strategic context: *why* work is happening.

**Tasks** -- the unit of trackable work. Tasks live inside a project and carry rich fields: title, description, plan, implementation, acceptance_criteria, effort (trivial through extreme), impact (trivial through extreme), category (feature, bugfix, refactor, etc.), group_key (flat grouping label), and status (todo, in_progress, done, archived).

**Documents** -- the knowledgebase layer. Documents are independent top-level entities with a title, content (markdown, up to 100k characters), and tags. They are linked to projects via a many-to-many relationship managed through `update_project` (attach_documents / detach_documents). Documents are designed for agent consumption: architecture decisions, established patterns, gotchas, and integration notes that make future planner, QA, and documenter runs more effective.

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
    |           +-- teach/
    |           +-- think/
    |
    +-- tab-for-projects/
          |
          +-- plugin.json          (name, agents, skills)
          +-- agents/
          |     +-- manager.md     (entry point, user-facing)
          |     +-- planner.md     (background subagent)
          |     +-- qa.md          (background subagent)
          |     +-- documenter.md  (background subagent)
          |     +-- coordinator.md (background subagent)
          |     +-- bugfixer.md    (foreground subagent)
          |     +-- implementer.md (background subagent)
          +-- skills/
                +-- design/
                +-- develop/
                +-- retro/
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
| (main thread)     |       |                           |
|                   |       |  +-------+ +------+ +---+ |
| - Conversation    |       |  |Project| | Task | |Doc| |
| - MCP CRUD        |       |  +-------+ +------+ +---+ |
| - Spawns agents   |       +---------------------------+
+--+-----+-----+---+
   |     |     |
   |     |     +--- foreground (run_in_background: false)
   |     |                |
   |     |                v
   |     |          +-----------+
   |     |          | Bugfixer  |
   |     |          |           |
   |     |          | - Talks   |
   |     |          |   to user |
   |     |          | - Fix bugs|
   |     |          | - Run     |
   |     |          |   tests   |
   |     |          +-----------+
   |     |
   |  background subagents (run_in_background: true)
   |     |
   v     v
+--------+ +--------+ +------------+ +-------------+ +-------------+
| Planner| |   QA   | | Documenter | | Coordinator | | Implementer |
|        | |        | |            | |             | |             |
| - Read | | - Read | | - Read     | | - Read MCP  | | - Read code |
|   code | |   code | |   code     | |   state     | | - Execute   |
| - Write| | - Check| | - Write    | | - Assess    | |   plans     |
|   tasks| |   work | |   docs     | |   health    | | - Self-     |
|   (MCP)| | - Write| | - Attach   | | - Dispatch  | |   validate  |
|        | |   tasks| |   to proj  | |   instrs    | | - Write MCP |
|        | |   (MCP)| |   (MCP)    | |   (MCP)     | |             |
+--------+ +--------+ +------------+ +-------------+ +-------------+
```

---

## Data Flow: tab-for-projects

A typical workflow from user request to completed, documented work:

1. **User talks to the manager.** Describes work they want to track or execute.
2. **Manager creates/updates project-level data** via the MCP (goal, requirements, design).
3. **Manager spawns the planner** in the background with the project ID and work description. The planner researches the codebase, decomposes the work into tasks with plans and acceptance criteria, and writes them to the MCP.
4. **User (or manager) triggers implementation.** Work happens on the tasks (via ad-hoc subagents or the user themselves).
5. **Manager spawns QA** in the background with the task IDs to validate. QA reads the MCP records and the actual codebase, compares what was planned against what was built, and writes verdicts. Failed tasks are reset to `todo`; gaps become new tasks under `group_key: "qa-findings"`.
6. **Manager spawns the documenter** in the background with completed task IDs. The documenter reads the tasks and codebase, extracts decisions and patterns, and writes them into MCP knowledgebase documents. These documents feed back into future planner and QA runs as additional context.

```
User --> Manager --> MCP (projects, tasks, documents)
              |
              +--> Coordinator  --> assesses project, dispatches work
              +--> Planner      --> writes tasks to MCP
              +--> Implementer  --> executes plans, updates tasks in MCP
              +--> QA           --> validates work, writes findings to MCP
              +--> Documenter   --> writes knowledge docs to MCP
              +--> Bugfixer     --> fixes bugs (foreground, talks to user)
                                       |
                                       v
                              Future planner/QA/coordinator runs
                              read these docs as context
```

The knowledge loop is the key architectural insight: the documenter captures what was learned, and future planner and QA runs consume that knowledge to produce better plans and more grounded reviews.
