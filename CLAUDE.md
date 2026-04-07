# Tab

Claude Code plugin marketplace containing two plugins: **tab** (a standalone personality/thinking-partner agent) and **tab-for-projects** (project management agents that talk to the Tab for Projects MCP). Published via `.claude-plugin/marketplace.json`.

## Repository Structure

```
.claude-plugin/marketplace.json   # Marketplace manifest — lists both plugins
README.md                         # Project README
LICENSE                           # Apache-2.0 license
scripts/validate-plugins.sh       # Plugin validation script
docs/                             # Documentation
  agent-teams.md                  #   Agent team structure and roles
  architecture.md                 #   Repository structure and design decisions
  project-agents.md               #   Project agents documentation
  setup.md                        #   Setup guide
  skills.md                       #   Skills documentation
  tab-agent.md                    #   Tab agent documentation
  walkthrough.md                  #   Walkthrough guide
tab/                              # "tab" plugin package
  .claude-plugin/plugin.json      #   Plugin metadata (agents, skills, version)
  settings.json                   #   Default agent: tab:Tab
  agents/tab.md                   #   Tab personality agent
  skills/draw-dino/SKILL.md       #   /draw-dino skill
  skills/listen/SKILL.md          #   /listen — deliberate listening mode
  skills/teach/SKILL.md           #   /teach — teaching and explanation mode
  skills/think/SKILL.md           #   /think — conversational idea capture
tab-for-projects/                 # "tab-for-projects" plugin package
  .claude-plugin/plugin.json      #   Plugin metadata (agents, skills, version)
  agents/project-manager.md       #   Project manager agent — project health, task shape, progress
  agents/developer.md             #   Developer agent — codebase owner, implementation, analysis, in-code docs
  agents/tech-lead.md             #   Tech-lead agent — KB owner, documentation via subagents, task decomposition
  skills/user-manual/SKILL.md          #   /user-manual — quickstart guide to using the plugin
```

## Package Architecture

- **tab** is standalone. One agent (`Tab`) with a rich personality system (profiles, settings 0-100%). No MCP dependency.
- **tab-for-projects** extends the ecosystem with three agents (project-manager, tech-lead, developer) and one skill (`/user-manual` — quickstart guide for users). All agents interact with the Tab for Projects MCP for project/task/document CRUD.
- Each package is independently installable. A `settings.json` at a package root can set the default agent via `{"agent": "<plugin>:<agent>"}`.

## Conventions

**Agents** are markdown files with YAML frontmatter (`name`, `description`). The body is the system prompt. Registered in `plugin.json` under `"agents"` as relative paths.

**Skills** live in `skills/<skill-name>/SKILL.md`. The body defines behavior, trigger rules, and output format. Registered in `plugin.json` via `"skills": "./skills/"` (directory reference). Skill frontmatter fields:

- `name` -- skill identifier, lowercase with hyphens, matches directory name. Parsed by the runtime.
- `description` -- what the skill does; the runtime uses this for trigger matching and catalog display. Parsed by the runtime.
- `argument-hint` -- (optional) pattern showing expected arguments (e.g., `"[topic]"`, `"<project ID>"`). Not parsed by the runtime, but useful as a quick-glance convention.

No other frontmatter fields should be added. Information about which agents run a skill, what mode it operates in, or what MCP servers it requires belongs in the skill body, not the frontmatter — duplicating it in YAML creates a maintenance trap and looks load-bearing when it isn't.

**Plugin metadata** lives in `<package>/.claude-plugin/plugin.json` with fields: `name`, `description`, `version`, `author`, `license`, `agents` (array of paths), `skills` (directory path).

**Marketplace manifest** at `.claude-plugin/marketplace.json` lists all plugins with `name`, `source`, `description`, `version`, `strict`.

## Key Files

| File | Purpose |
|------|---------|
| `.claude-plugin/marketplace.json` | Marketplace plugin registry |
| `scripts/validate-plugins.sh` | Plugin validation script |
| `tab/.claude-plugin/plugin.json` | Tab plugin manifest |
| `tab-for-projects/.claude-plugin/plugin.json` | Tab for Projects plugin manifest |
| `tab/agents/tab.md` | Tab agent — personality, profiles, settings |
| `tab-for-projects/agents/project-manager.md` | Project manager — project health, task shape, progress signals |
| `tab-for-projects/agents/developer.md` | Developer agent — codebase owner, implementation, analysis, in-code docs |
| `tab-for-projects/agents/tech-lead.md` | Tech-lead agent — KB owner, documentation via subagents, task decomposition |
| `tab/settings.json` | Tab default agent config |
| `docs/` | Project documentation (architecture, setup, skills, agents, walkthrough) |
