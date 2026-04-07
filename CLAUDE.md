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
  skills/user-manual/SKILL.md          #   /user-manual — unified reference router
  skills/user-manual/refs/mcp.md      #   MCP data model, tools, and patterns
  skills/user-manual/refs/documents.md #   Document discipline and conventions
  skills/user-manual/refs/agents.md   #   Agent and skill authoring patterns
```

## Package Architecture

- **tab** is standalone. One agent (`Tab`) with a rich personality system (profiles, settings 0-100%). No MCP dependency.
- **tab-for-projects** extends the ecosystem with three agents (project-manager, tech-lead, developer) and one skill (`/user-manual` with four reference modules). All agents interact with the Tab for Projects MCP for project/task/document CRUD.
- Each package is independently installable. A `settings.json` at a package root can set the default agent via `{"agent": "<plugin>:<agent>"}`.

## Conventions

**Agents** are markdown files with YAML frontmatter (`name`, `description`). The body is the system prompt. Registered in `plugin.json` under `"agents"` as relative paths.

**Skills** live in `skills/<skill-name>/SKILL.md`. Frontmatter fields: `name`, `description`, `argument-hint`. Extended frontmatter fields for workflow skills: `inputs` (structured argument spec), `mode` (headless/conversational/foreground), `agents` (which agent runs the skill), `requires-mcp` (MCP dependency). The body defines behavior, trigger rules, and output format. Registered in `plugin.json` via `"skills": "./skills/"` (directory reference).

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
