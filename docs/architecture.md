# Architecture Overview

> **Maintaining this document:** verify against these source files when updating.
>
> - `/.claude-plugin/marketplace.json` -- marketplace registration
> - `/tab/.claude-plugin/plugin.json` -- tab plugin manifest
> - `/tab-for-projects/.claude-plugin/plugin.json` -- tab-for-projects plugin manifest
> - `/tab/settings.json` -- tab default agent setting
> - `/tab/agents/tab.md` -- Tab agent definition
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
| Agent: developer | `/tab-for-projects/agents/developer.md` | Codebase owner -- implementation, analysis, in-code docs |

### Architecture

The plugin has one agent (developer). The developer agent owns the codebase: it receives tasks with plans, gathers context from KB documents and the codebase, implements the solution, maintains in-code documentation (CLAUDE.md files), verifies with tests, and commits from worktrees.

### The Three MCP Data Layers

The Tab for Projects MCP organizes data into three layers, each with list/get/create/update operations:

**Projects** -- the top-level container. A project has a title, goal, requirements, and design. These fields capture the strategic context: *why* work is happening.

**Tasks** -- the unit of trackable work. Tasks live inside a project and carry rich fields: title, description, plan, implementation, acceptance_criteria, effort (trivial through extreme), impact (trivial through extreme), category (feature, bugfix, refactor, etc.), group_key (flat grouping label), and status (todo, in_progress, done, archived).

**Documents** -- the knowledgebase layer. Documents are independent top-level entities with a title, content (markdown, up to 100k characters), and tags. They are linked to projects via a many-to-many relationship managed through `update_project` (attach_documents / detach_documents). Documents are designed for agent consumption: architecture decisions, established patterns, gotchas, and integration notes that make future runs more effective. Skills handle KB document creation and curation inline.

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
                +-- developer.md        (codebase owner)

```

### tab-for-projects Internal Architecture

The developer agent is the sole component. It interacts directly with the Tab for Projects MCP for project, task, and document operations, and owns all codebase work.

```
+-------------------+
|      User         |
+--------+----------+
         |
         v
+--------+----------+       +---------------------------+
|    Developer      |<----->|   Tab for Projects MCP    |
|                   |       |                           |
| - Read code       |       |  +-------+ +------+ +---+ |
| - Implement       |       |  |Project| | Task | |Doc| |
| - Test            |       |  +-------+ +------+ +---+ |
| - Commit          |       +---------------------------+
| - CLAUDE.md       |
+-------------------+
```

---

## Data Flow: tab-for-projects

A typical workflow from user request to completed, documented work:

1. **User describes work** to the developer agent. The agent manages project context, task shape, and KB concerns via the MCP.
2. **Developer reads the codebase and writes KB documents** (design docs, ADRs, codebase patterns, conventions). For planning work, decomposes scope into dependency-ordered task graphs.
3. **Developer implements ready tasks** in worktrees. Gathers context from the task plan and linked KB documents, implements, tests, and commits.
4. **Developer captures knowledge** from completed work -- reads implemented code, compares to the plan, and updates KB documents.

```
User --> Developer --> MCP (projects, tasks, documents)
              |
              +--> manages project health, task shape
              +--> writes KB docs, decomposes tasks
              +--> implements tasks, commits
              |
              v
         Future runs read these docs as context
```

The knowledge loop is the key architectural insight: knowledge captured after implementation feeds future runs, producing better designs, more accurate codebase docs, and more grounded task plans.
