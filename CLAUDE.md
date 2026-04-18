# Tab

Claude Code plugin marketplace containing two plugins: **tab** (a standalone personality/thinking-partner agent) and **tab-for-projects** (autonomous subagents and workflow skills that talk to the Tab for Projects MCP). Published via `.claude-plugin/marketplace.json`.

## Repository Structure

```
.claude-plugin/marketplace.json   # Marketplace manifest — lists both plugins
README.md                         # Project README
LICENSE                           # Apache-2.0 license
scripts/validate-plugins.sh       # Plugin validation script
tab/                              # "tab" plugin package
  .claude-plugin/plugin.json      #   Plugin metadata (agents, skills, version)
  CHANGELOG.md                    #   Release notes (keep-a-changelog)
  settings.json                   #   Default agent: tab:Tab
  agents/tab.md                   #   Tab personality agent
  skills/draw-dino/SKILL.md       #   /draw-dino skill
  skills/hey-tab/SKILL.md         #   /hey-tab — setup instructions for MCPs
  skills/listen/SKILL.md          #   /listen — deliberate listening mode
  skills/teach/SKILL.md           #   /teach — teaching and explanation mode
  skills/think/SKILL.md           #   /think — conversational idea capture
tab-for-projects/                 # "tab-for-projects" plugin package
  .claude-plugin/plugin.json      #   Plugin metadata (agents, skills, version)
  CHANGELOG.md                    #   Release notes (keep-a-changelog)
  agents/implementer.md           #   Implementer subagent — takes one ready task, writes code, verifies, commits; files tasks for follow-ups (no KB writes)
  agents/architect.md             #   Architect subagent — produces design docs and ADRs from design/feature tasks
  agents/test-writer.md           #   Test-writer subagent — pins current behavior with tests; suspicious behavior becomes a new bugfix task
  agents/docs-writer.md           #   Docs-writer subagent — produces READMEs, CHANGELOG prose, upgrade guides, reference docs; KB-doc authority
  skills/plan-project/SKILL.md    #   /plan-project — interview + research + decompose into a groomed backlog
  skills/feature/SKILL.md         #   /feature — capture a feature idea as 1+ tasks on the backlog
  skills/fix/SKILL.md             #   /fix — file a single task from conversation
  skills/manage-backlog/SKILL.md  #   /manage-backlog — groom todos up to the readiness bar
  skills/work/SKILL.md            #   /work — autonomously execute the ready portion of the backlog
  skills/search/SKILL.md          #   /search — find docs and tasks via an escalating filter ladder
  skills/get-project/SKILL.md     #   /get-project — pull a project snapshot for orientation
  skills/save-document/SKILL.md   #   /save-document — capture a decision, convention, or reference doc
```

## Package Architecture

- **tab** is standalone. One agent (`Tab`) with a rich personality system (profiles, settings 0-100%). No MCP dependency.
- **tab-for-projects** extends the ecosystem with autonomous subagents (implementer, architect) that `/work` routes tasks to by category, plus a set of verb-shaped workflow skills that automate high-friction operations against the Tab for Projects MCP. Each skill is a one-shot automation, not an ambient mode. Skills resolve the active project via inference (explicit arg → `.tab-project` file → git remote → cwd → recent activity) and respect a shared task-readiness bar defined in the KB.
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

## Validation

Run `bash scripts/validate-plugins.sh` from the repo root after any structural change — adding/removing skills, agents, or updating plugin metadata. It checks:

- Agent and skill paths resolve correctly
- Frontmatter is valid
- Versions are in sync between marketplace and plugin.json
- CLAUDE.md structure tree matches what's actually on disk

If you add or remove a skill/agent, update the Repository Structure tree above and run the validator. It will fail if the tree is out of date.

## Versioning and Changelogs

Bump the version in both `plugin.json` and `marketplace.json` as part of any commit that changes a plugin's behavior — new skills, agent prompt changes, bug fixes. The validator enforces that versions stay in sync across the two files, so always update both together.

Use semver: patch for fixes and minor prompt tweaks, minor for new skills or meaningful behavior changes, major for breaking changes. When in doubt, bump minor.

**Every version bump must include a changelog entry.** Each plugin has a `CHANGELOG.md` at its package root (`tab/CHANGELOG.md`, `tab-for-projects/CHANGELOG.md`) following the [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) format. Add a new `## [version] — YYYY-MM-DD` section above the previous one with `### Added`, `### Changed`, `### Fixed`, or `### Removed` subsections as appropriate. Write entries for users, not for yourself — describe what changed from their perspective and why it matters, not the implementation detail.

## Key Files

| File | Purpose |
|------|---------|
| `.claude-plugin/marketplace.json` | Marketplace plugin registry |
| `scripts/validate-plugins.sh` | Plugin validation script |
| `tab/.claude-plugin/plugin.json` | Tab plugin manifest |
| `tab/CHANGELOG.md` | Tab plugin release notes |
| `tab-for-projects/.claude-plugin/plugin.json` | Tab for Projects plugin manifest |
| `tab-for-projects/CHANGELOG.md` | Tab for Projects plugin release notes |
| `tab/agents/tab.md` | Tab agent — personality, profiles, settings |
| `tab-for-projects/agents/implementer.md` | Implementer subagent — takes one ready task, writes code, verifies, commits; files tasks for follow-ups (no KB writes) |
| `tab-for-projects/agents/architect.md` | Architect subagent — produces design docs and ADRs from design/feature tasks |
| `tab/settings.json` | Tab default agent config |
