# Architecture Overview

> **Maintaining this document:** verify against these source files when updating.
>
> - `/.claude-plugin/marketplace.json` -- marketplace registration
> - `/tab/.claude-plugin/plugin.json` -- tab plugin manifest
> - `/tab-for-projects/.claude-plugin/plugin.json` -- tab-for-projects plugin manifest
> - `/tab/settings.json` -- tab default agent setting
> - `/tab/agents/tab.md` -- Tab agent definition
> - `/tab-for-projects/agents/project-manager.md` -- project-manager agent
> - `/tab-for-projects/agents/tech-lead.md` -- tech-lead agent (KB owner)
> - `/tab-for-projects/agents/developer.md` -- developer agent (codebase owner)

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

A plugin may have a `settings.json` at its root that sets the default agent:

- **tab:** `{ "agent": "tab:Tab" }`

The format is `plugin-name:agent-name`. Not all plugins require a settings file.

---

## tab Package

**Purpose:** Defines the Tab personality -- a thinking partner with configurable personality settings. Tab helps users sharpen ideas, pressure-test plans, and make better decisions.

### Components

| Component | Path | Role |
|-----------|------|------|
| Agent: Tab | `/tab/agents/tab.md` | The sole agent -- defines identity, personality, constraints, and profiles |
| Skill: draw-dino | `/tab/skills/draw-dino` | Draw ASCII art dinosaurs |
| Skill: listen | `/tab/skills/listen` | Deliberate listening mode |
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
| Agent: project-manager | `/tab-for-projects/agents/project-manager.md` | Project health -- diagnoses projects, fixes task shape, progress signals |
| Agent: tech-lead | `/tab-for-projects/agents/tech-lead.md` | KB owner -- documentation via subagents, task decomposition |
| Agent: developer | `/tab-for-projects/agents/developer.md` | Codebase owner -- implementation, analysis, in-code docs |
| Skill: kickoff | `/tab-for-projects/skills/kickoff` | Take an idea and stand up a fully-formed project |
| Skill: plan | `/tab-for-projects/skills/plan` | Design and decompose a feature into tasks |
| Skill: build | `/tab-for-projects/skills/build` | Multi-task execution loop |
| Skill: investigate | `/tab-for-projects/skills/investigate` | Understand how something works in the codebase |
| Skill: status | `/tab-for-projects/skills/status` | Quick project health brief |
| Skill: maintain | `/tab-for-projects/skills/maintain` | Housekeeping sweep -- task shape, KB curation |
| Skill: review | `/tab-for-projects/skills/review` | Retrospective -- did we build what we planned? |
| Skill: user-manual | `/tab-for-projects/skills/user-manual` | Quickstart guide to using the plugin |


### Agent Roles

Each agent owns a distinct domain. Skills orchestrate agents as needed -- there is no dedicated orchestration agent.

**Project Manager** (`project-manager`): Owns project health. Dispatched to diagnose projects, fix task shape and project fields, and report progress signals. Does not touch the codebase or KB documents directly.

**Tech Lead** (`tech-lead`): Owns the knowledgebase. Reads code to understand actual patterns, writes and curates KB documents (design docs, ADRs, conventions, codebase patterns). Also decomposes work into dependency-ordered task graphs with descriptions, plans, acceptance criteria, and effort estimates.

**Developer** (`developer`): Owns the codebase. Receives tasks with plans, gathers context from KB documents and the codebase, implements the solution, maintains in-code documentation (CLAUDE.md files), verifies with tests, and commits from worktrees.

### The Three MCP Data Layers

The Tab for Projects MCP organizes data into three layers, each with list/get/create/update operations:

**Projects** -- the top-level container. A project has a title, goal, requirements, and design. These fields capture the strategic context: *why* work is happening.

**Tasks** -- the unit of trackable work. Tasks live inside a project and carry rich fields: title, description, plan, implementation, acceptance_criteria, effort (trivial through extreme), impact (trivial through extreme), category (feature, bugfix, refactor, etc.), group_key (flat grouping label), and status (todo, in_progress, done, archived).

**Documents** -- the knowledgebase layer. Documents are independent top-level entities with a title, content (markdown, up to 100k characters), and tags. They are linked to projects via a many-to-many relationship managed through `update_project` (attach_documents / detach_documents). Documents are designed for agent consumption: architecture decisions, established patterns, gotchas, and integration notes that make future advisory runs more effective. The tech lead writes all KB documents — design docs, ADRs, codebase patterns, and conventions.

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
          |     +-- project-manager.md  (project health)
          |     +-- tech-lead.md        (KB owner)
          |     +-- developer.md        (codebase owner)
          +-- skills/
                +-- kickoff/       (new project ceremony)
                +-- plan/          (feature decomposition)
                +-- build/         (multi-task execution)
                +-- investigate/   (codebase understanding)
                +-- status/        (project health brief)
                +-- maintain/      (housekeeping sweep)
                +-- review/        (retrospective)
                +-- user-manual/   (quickstart guide)

```

### tab-for-projects Internal Architecture

Skills orchestrate agents against the MCP. Each skill defines which agents it dispatches and in what order.

```
+-------------------+
|      User         |
+--------+----------+
         |
         | invokes skill (e.g., /build, /kickoff)
         v
+--------+----------+       +---------------------------+
|   Skill (runner)  |<----->|   Tab for Projects MCP    |
|                   |       |                           |
| dispatches agents |       |  +-------+ +------+ +---+ |
| per skill spec    |       |  |Project| | Task | |Doc| |
+--+-----+-----+---+       |  +-------+ +------+ +---+ |
   |     |     |            +---------------------------+
   v     v     v
+----------+ +-----------+ +-----------+
| Project  | | Tech Lead | | Developer |
| Manager  | |           | |           |
|          | | - Read    | | - Read    |
| - Diag-  | |   code    | |   code    |
|   nose   | | - Write   | | - Implement|
|   project| |   KB docs | | - Test    |
| - Fix    | | - Write   | | - Commit  |
|   tasks  | |   tasks   | | - CLAUDE  |
| - Report | | - Curate  | |   .md     |
|   health | |   KB      | |           |
+----------+ +-----------+ +-----------+
```

---

## Data Flow: tab-for-projects

A typical workflow from user request to completed, documented work:

1. **User invokes a skill** (e.g., `/kickoff`, `/build`, `/plan`). The skill defines which agents are dispatched.
2. **Project manager diagnoses project health** -- checks task shape, project fields, progress signals.
3. **Tech lead reads the codebase and writes KB documents** (design docs, ADRs, codebase patterns, conventions). For planning work, decomposes scope into dependency-ordered task graphs.
4. **Developer implements ready tasks** in worktrees. Gathers context from the task plan and linked KB documents, implements, tests, and commits.
5. **Tech lead captures knowledge** from completed work -- reads implemented code, compares to the plan, and updates KB documents.

```
User --> Skill --> MCP (projects, tasks, documents)
           |
           +--> Project Manager --> diagnoses project, fixes task shape
           +--> Tech Lead       --> writes KB docs, decomposes tasks
           +--> Developer       --> implements tasks, commits
                                       |
                                       v
                              Tech Lead captures knowledge
                              from completed work
                                       |
                                       v
                              Future runs read these docs
                              as context
```

The knowledge loop is the key architectural insight: the tech lead captures what was learned after implementation, and future runs consume that knowledge to produce better designs, more accurate codebase docs, and more grounded task plans.
