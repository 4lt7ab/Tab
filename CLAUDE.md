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
  agents/manager.md               #   Project manager agent — orchestration layer
  agents/designer.md              #   Designer agent — system design and task planning
  agents/planner.md               #   Planner agent — task decomposition
  agents/developer.md             #   Developer agent — implementation and commits
  agents/tech-lead.md             #   Tech-lead agent — codebase truth, pattern docs, drift corrections
  skills/agentic-reference/SKILL.md   #   /agentic-reference — agent and skill authoring patterns
  skills/document/SKILL.md            #   /document — knowledge extraction from completed work
  skills/document-reference/SKILL.md  #   /document-reference — advisory agent document discipline
  skills/mcp-reference/SKILL.md       #   /mcp-reference — Tab for Projects MCP reference
  skills/prompt-reference/SKILL.md    #   /prompt-reference — prompt quality conventions
```

## Package Architecture

- **tab** is standalone. One agent (`Tab`) with a rich personality system (profiles, settings 0-100%). No MCP dependency.
- **tab-for-projects** extends the ecosystem with five agents in a three-layer model (manager, designer, tech-lead, planner, developer) and five skills (`/agentic-reference`, `/document`, `/document-reference`, `/mcp-reference`, `/prompt-reference`). All agents interact with the Tab for Projects MCP for project/task/document CRUD.
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
| `tab-for-projects/agents/manager.md` | Project manager agent (default for tab-for-projects) |
| `tab-for-projects/agents/designer.md` | Designer agent — system design and task planning |
| `tab-for-projects/agents/planner.md` | Planner agent — task decomposition |
| `tab-for-projects/agents/developer.md` | Developer agent — implementation and commits |
| `tab-for-projects/agents/tech-lead.md` | Tech-lead agent — codebase truth, pattern docs, drift corrections |
| `tab/settings.json` | Tab default agent config |
| `docs/` | Project documentation (architecture, setup, skills, agents, walkthrough) |
