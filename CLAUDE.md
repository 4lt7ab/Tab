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
  settings.json                   #   Default agent: tab:Tab
  agents/tab.md                   #   Tab personality agent
  skills/draw-dino/SKILL.md       #   /draw-dino skill
  skills/hey-tab/SKILL.md         #   /hey-tab — setup instructions for MCPs
  skills/listen/SKILL.md          #   /listen — deliberate listening mode
  skills/teach/SKILL.md           #   /teach — teaching and explanation mode
  skills/think/SKILL.md           #   /think — conversational idea capture
tab-for-projects/                 # "tab-for-projects" plugin package
  .claude-plugin/plugin.json      #   Plugin metadata (agents, skills, version)
  agents/archaeologist.md         #   Archaeologist subagent — autonomous design synthesis; reads code + project KB, produces structured design summary; closes design tasks on clean synthesis, picks sane defaults and flags them on real forks; no KB writes, no code edits
  agents/bug-hunter.md            #   Bug-hunter subagent — targeted codebase investigation; structured report with file+line anchors; no edits, no backlog writes
  agents/developer.md             #   Developer subagent — worktree-only; atomic on code + tests; commits in the worktree; never merges
  agents/project-planner.md       #   Project-planner subagent — expert codebase reader; takes a well-formed prompt and acts on the project backlog: creates tasks for uncaptured work, grooms below-bar tasks to the quality bar for their effort, searches the KB, reads the codebase; falls back to design tickets for forks it can't resolve; no KB writes, no code edits
  skills/design/SKILL.md          #   /design — conversational KB authorship for project-shape work and design-category tasks; sole entry point for KB writes
  skills/develop/SKILL.md         #   /develop — conversational pair-programming mode; surveys code + KB + backlog, shapes a lightweight plan, iterates test-first on the working tree; opt-in developer dispatches to worktrees for bounded sub-scopes
  skills/plan/SKILL.md            #   /plan — intent-to-backlog; modes: intent / survey / groom / rewrite; shapes a planner dispatch, confirms before handoff, planner writes directly; parallel planners on large scopes, one level deep
  skills/search/SKILL.md          #   /search — find docs and tasks via an escalating filter ladder
  skills/ship/SKILL.md            #   /ship — pre-push sweep: version bump, README/CLAUDE.md drift review
  skills/work/SKILL.md            #   /work — autopilot backlog execution: developer-in-worktree for implementation tasks, archaeologist for design tasks; below-bar surfaces for /plan groom, archaeologist-escalated forks surface for /design
```

## Package Architecture

- **tab** is standalone. One agent (`Tab`) with a rich personality system (profiles, settings 0-100%). No MCP dependency.
- **tab-for-projects** extends the ecosystem with four subagents (`developer`, `project-planner`, `bug-hunter`, `archaeologist`) and six verb-shaped workflow skills that automate high-friction operations against the Tab for Projects MCP. `archaeologist` is the autonomous design-synthesis path — reads project code and KB, returns a structured design summary, closes design tasks on clean synthesis (picks sane defaults and flags them when real forks surface). `/work` dispatches `developer` in isolated git worktrees for implementation tasks and `archaeologist` on the main thread for design-category tasks — below-bar tasks surface for `/plan groom`, archaeologist-escalated forks surface for `/design`. `/develop` is the conversational counterpart to `/work`: takes prose intent, surveys the code + KB + backlog, shapes a lightweight plan, and iterates test-first on the user's working tree, with opt-in `developer` dispatches to worktrees for bounded sub-scopes. Grooming never happens inside `/work`; the old "groom-then-dispatch" path was the source of an infinite-loop failure mode and is gone. `/plan` is the intent-to-backlog skill (intent / survey / groom / rewrite modes) and the primary caller of `project-planner`; `/plan` shapes the dispatch (one planner call, or parallel planners for large scopes — one level deep), confirms it with the user, and hands off a well-formed prompt. The planner writes tasks directly — the confirm gate is upstream, at dispatch time. `/plan` (rewrite mode) dispatches `bug-hunter` for codebase investigation. `/design` owns all KB authorship and dispatches `archaeologist` for code + KB synthesis research plus the `exa` MCP for external analogues; `bug-hunter` stays available for runtime-bug concerns that masquerade as design forks. `/ship` owns cross-cutting doc sweeps (README, CLAUDE.md) at the pre-push checkpoint as a coherent pass: changelog synthesis, version bump, drift review. Skills resolve the active project via inference (explicit arg → `.tab-project` file → git remote → cwd → recent activity) and respect a shared task-readiness bar.
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

## Versioning

Bump the version in both `plugin.json` and `marketplace.json` as part of any commit that changes a plugin's behavior — new skills, agent prompt changes, bug fixes. The validator enforces that versions stay in sync across the two files, so always update both together.

Use semver: patch for fixes and minor prompt tweaks, minor for new skills or meaningful behavior changes, major for breaking changes. When in doubt, bump minor.

This repo does not maintain a changelog — git history is the source of truth for what changed.

## Commit Messages

Short. Wordplay over summary. The diff already says *what* changed — the subject line is flavor, not a recap.

Riff on the code being committed: a pun, a callback, a phrase that fits. Aim for under ~40 chars. Drop the conventional-commit prefix (`fix:`, `feat:`) unless it's part of the joke.

Recent examples to calibrate against:

- `always be shufflin'`
- `fix: no more changelogs`

If the joke doesn't land in a line, it's too much. A body is fine when context genuinely needs it, but the subject stays terse.

## Key Files

| File | Purpose |
|------|---------|
| `.claude-plugin/marketplace.json` | Marketplace plugin registry |
| `scripts/validate-plugins.sh` | Plugin validation script |
| `tab/.claude-plugin/plugin.json` | Tab plugin manifest |
| `tab-for-projects/.claude-plugin/plugin.json` | Tab for Projects plugin manifest |
| `tab/agents/tab.md` | Tab agent — personality, profiles, settings |
| `tab-for-projects/agents/archaeologist.md` | Archaeologist subagent — autonomous design synthesis; reads code + project KB, returns a structured summary with resolved and flagged decisions; closes design tasks on clean synthesis; no KB writes, no code edits |
| `tab-for-projects/agents/developer.md` | Developer subagent — worktree-only; writes code + tests atomically; commits in the worktree; never merges |
| `tab-for-projects/agents/project-planner.md` | Project-planner subagent — expert codebase reader; takes a well-formed prompt and acts on the project backlog: creates tasks for uncaptured work, grooms below-bar tasks to the quality bar for their effort, searches the KB, reads the codebase; falls back to design tickets for forks it can't resolve; never writes KB docs, never edits code |
| `tab-for-projects/agents/bug-hunter.md` | Bug-hunter subagent — targeted investigation returning a structured report with file + line anchors and explicit confidence levels; does not edit code or touch the backlog |
| `tab/settings.json` | Tab default agent config |
