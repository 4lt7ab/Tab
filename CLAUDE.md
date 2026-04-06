# Tab

Claude Code plugin marketplace containing two plugins: **tab** (a standalone personality/thinking-partner agent) and **tab-for-projects** (project management agents that talk to the Tab for Projects MCP). Published via `.claude-plugin/marketplace.json`.

## Repository Structure

```
.claude-plugin/marketplace.json   # Marketplace manifest — lists both plugins
README.md                         # Project README
LICENSE                           # Apache-2.0 license
scripts/validate-plugins.sh       # Plugin validation script
docs/                             # Documentation
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
  skills/listen/SKILL.md          #   /listen — deliberate listening mode
  skills/draw-dino/SKILL.md       #   /draw-dino skill
  skills/brainstorm/SKILL.md      #   /brainstorm — conversational idea capture
tab-for-projects/                 # "tab-for-projects" plugin package
  .claude-plugin/plugin.json      #   Plugin metadata (agents, skills, version)
  settings.json                   #   Default agent: tab-for-projects:manager
  agents/CONVENTIONS.md           #   Shared agent conventions
  agents/manager.md               #   Project manager agent
  agents/planner.md               #   Planning agent
  agents/qa.md                    #   QA agent
  agents/documenter.md            #   Documentation agent
  agents/coordinator.md           #   Coordinator agent
  agents/bugfixer.md              #   Bugfixer agent
  agents/implementer.md           #   Implementer agent
  agents/team-lead.md             #   Team-lead agent — ad-hoc requests and knowledgebase expertise
  skills/refinement/SKILL.md      #   /refinement — backlog refinement ceremony
  skills/bugfix/SKILL.md          #   /bugfix — focused bugfix session
  skills/autopilot/SKILL.md       #   /autopilot — autonomous project coordination
```

## Package Architecture

- **tab** is standalone. One agent (`Tab`) with a rich personality system (profiles, settings 0-100%). No MCP dependency.
- **tab-for-projects** extends the ecosystem with seven specialized agents and three skills (`/refinement`, `/bugfix`, `/autopilot`). All agents interact with the Tab for Projects MCP for project/task/document CRUD.
- Each package is independently installable. `settings.json` at each package root sets the default agent via `{"agent": "<plugin>:<agent>"}`.

## Conventions

**Agents** are markdown files with YAML frontmatter (`name`, `description`). The body is the system prompt. Registered in `plugin.json` under `"agents"` as relative paths.

**Skills** live in `skills/<skill-name>/SKILL.md`. Frontmatter fields: `name`, `description`, `argument-hint`. The body defines behavior, trigger rules, and output format. Registered in `plugin.json` via `"skills": "./skills/"` (directory reference).

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
| `tab-for-projects/agents/manager.md` | Project manager agent (default for tab-for-projects) |
| `tab-for-projects/agents/coordinator.md` | Coordinator agent |
| `tab-for-projects/agents/bugfixer.md` | Bugfixer agent |
| `tab-for-projects/agents/implementer.md` | Implementer agent — executes task plans |
| `tab-for-projects/agents/team-lead.md` | Team-lead agent — ad-hoc requests and knowledgebase expertise |
| `tab-for-projects/agents/CONVENTIONS.md` | Shared agent conventions |
| `tab/settings.json` | Tab default agent config |
| `tab-for-projects/settings.json` | Tab for Projects default agent config |
| `docs/` | Project documentation (architecture, setup, skills, agents, walkthrough) |
