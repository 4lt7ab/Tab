# Tab

Personality, workflows, and skills defined in plain markdown — runtimes are interchangeable.

Two runtimes live here:

- **Claude Code plugins** under `plugins/`: **tab** (a standalone personality/thinking-partner agent) and **tab-for-projects** (autonomous subagents and workflow skills that talk to the Tab for Projects MCP). Published via `.claude-plugin/marketplace.json`.
- **Tab CLI** under `cli/`: a Python package (`tab`) that runs the same markdown substrate outside Claude Code — multi-provider via pydantic-ai, semantic-gated skill routing via grimoire, exposable as an MCP server.

The markdown is the source of truth; the runtimes read it.

## Repository Structure

```
.claude-plugin/marketplace.json     # Marketplace manifest — lists both plugins
README.md                           # Project README
LICENSE                             # Apache-2.0 license
scripts/validate-plugins.sh         # Plugin validation script
cli/                                # Tab CLI — Python runtime for the markdown substrate
  pyproject.toml                    #   Package metadata; entry point: `tab` -> tab_cli.cli:app
  src/tab_cli/                      #   Typer app, personality compiler, grimoire registry, Ollama-native model, MCP server
  tests/                            #   pytest suite
plugins/
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
    agents/advocate.md              #   Advocate subagent — adversarial position-defender; takes assigned position + archaeologist report + design question, returns strongest case with file/line and doc/passage anchors; explicitly non-neutral; dispatched by /design in parallel after archaeologist runs on contested decisions; no KB writes, no code edits
    agents/archaeologist.md         #   Archaeologist subagent — three caller modes: autonomous design synthesis closing design tasks (for /develop), research briefer ahead of human-hosted /design conversations, and north-star synthesis proposing edits to favorited docs against a version brief (for /ship); no KB writes, no code edits
    agents/bug-hunter.md            #   Bug-hunter subagent — targeted codebase investigation; structured report with file+line anchors and confidence levels; called by /design (runtime forks), /qa (runtime side of a version audit), or directly; no edits, no backlog writes
    agents/developer.md             #   Developer subagent — worktree-only; atomic on code + tests; commits in the worktree; never merges; called by /develop
    agents/project-planner.md       #   Project-planner subagent — expert codebase reader; called by /design (after the brief) and /curate (slotting loose inbox work into an in-progress version); creates tasks for uncaptured work, grooms below-bar tasks to the quality bar for their effort, searches the KB, reads the codebase; falls back to design tickets for forks it can't resolve; no KB writes, no code edits
    skills/curate/SKILL.md          #   /curate — manual-only inbox drain: pulls group_key="new" plus other loose tasks, dispatches project-planner to groom and slot them into an existing in-progress version; target group inferred when exactly one version is in progress; --dry-run prints the slate without writing; cannot open new versions (refers user to /design); cannot write KB; no other skill suggests it
    skills/design/SKILL.md          #   /design — version-anchored conversational KB authorship; commits to a version on entry (open new or extend in-progress) and announces the pick + goal, draws out one goal as the filter, dispatches archaeologist for evidence then advocates in parallel on contested decisions; pre-dispatch preview shows brief + version slug + task fan-out then applies (interrupt to redirect); --dry-run stops after preview; sole entry point for KB writes; only skill that opens new versions
    skills/discuss/SKILL.md         #   /discuss — pre-design scoping via multi-agent roundtable; read-only (no KB writes, no task writes, no version commit); announces framing and proceeds; dispatches archaeologist for evidence, advocates in parallel on contested direction forks, and project-planner-as-thinker on task-shape forks; closes with a recommendation (`/design`, `/jot`, done, or needs-scoping) for the user to invoke
    skills/develop/SKILL.md         #   /develop — version-anchored autopilot; takes optional group_key (infers the most-recently-active in-progress group when omitted; refuses "new"), reads the dependency graph, dispatches developer in parallel worktrees for unblocked tasks, FF-merges the first returning dev / --no-ff for the second-and-later, halts on dirty tree / three failures / merge content conflict / interrupt, supports --dry-run, ends by suggesting /qa <group_key>
    skills/jot/SKILL.md             #   /jot — one-shot capture into the reserved inbox group_key="new"; title required (synthesized silently from the prior utterance when omitted), optional summary/category; never asks follow-up questions; no codebase/KB reads; no planner dispatch
    skills/qa/SKILL.md              #   /qa — version audit orchestrator: takes optional group_key (infers the most-recently-active in-progress group when omitted; refuses "new"), dispatches bug-hunter (runtime) and archaeologist (alignment) in parallel, files concrete gap tasks into the same group, surfaces complexity/risk for the user
    skills/search/SKILL.md          #   /search — find docs and tasks via an escalating filter ladder
    skills/ship/SKILL.md            #   /ship — pre-push sweep capping a version: bumps the code version, reviews README/CLAUDE.md drift (skippable via --skip-docs), dispatches archaeologist to synthesize edits to favorited north-star docs against the version brief, deletes the brief, prints the full preview then applies (--dry-run stops after preview), packages KB writes + code edits in a single commit; does not push
```

## Package Architecture

Two Claude Code plugins (`plugins/tab`, `plugins/tab-for-projects`) and one Python runtime (`cli/`). All three sit on the same markdown substrate — `agents/*.md` and `skills/*/SKILL.md` under `plugins/tab/` — so personality and skill changes flow to whichever runtime loads them.

- **tab** (Claude Code plugin) is standalone. One agent (`Tab`) with a rich personality system (profiles, settings 0-100%). No MCP dependency.
- **tab-for-projects** (Claude Code plugin) extends the ecosystem with five subagents (`developer`, `project-planner`, `bug-hunter`, `archaeologist`, `advocate`) and eight verb-shaped workflow skills (`jot`, `curate`, `design`, `discuss`, `develop`, `qa`, `ship`, `search`) that automate high-friction operations against the Tab for Projects MCP. The shared interaction convention across writing skills is announce-and-proceed: invocation is consent, so each skill prints what it's about to do, announces it's doing it, and proceeds — `--dry-run` is the opt-in flag for preview-only, and refusal stays only for category errors and unrecoverable cases. Arguments are inferred where recoverable: `/jot` synthesizes a missing title from the prior utterance; `/develop` and `/qa` infer the most-recently-active in-progress group when `group_key` is omitted; `/curate` infers the target version when exactly one is in progress. The lifecycle is version-anchored: `/jot` captures friction-free into the reserved inbox `group_key="new"`; `/curate` (manual-only — no other skill suggests it) drains the inbox into an existing in-progress version, dispatching `project-planner` to groom each candidate as it slots; `/design` opens a new version (or extends one in progress), announces the version pick and the chosen goal and proceeds, and on contested decisions dispatches `archaeologist` once for the evidence base then `advocate` agents in parallel for the strongest case per position — it is the sole entry point for KB writes and the only skill that opens new versions; `/discuss` runs read-only roundtables (no KB writes, no task writes, no version commit), announces its framing and proceeds, dispatches `archaeologist` for the evidence base, `advocate` agents in parallel on contested direction forks, and `project-planner-as-thinker` on task-shape forks (decomposition / seams / slicing), and closes with a recommendation the user invokes themselves; `/develop` is autopilot, refuses `"new"`, reads the dependency graph, and dispatches `developer` in isolated git worktrees in parallel for the unblocked frontier, FF-merging the first returning dev's branch and --no-ff-merging the second-and-later in a parallel batch, halting on dirty tree, three consecutive failures, merge content conflict, or user interrupt — grooming never happens inside `/develop`, and the old groom-then-dispatch path that lived there is gone; `/qa` audits one version (also refuses `"new"`), dispatching `bug-hunter` for the runtime side and `archaeologist` for KB/code alignment in parallel, filing concrete gap tasks into the same group and surfacing complexity/risk for the user without auto-filing design tasks; `/ship` caps a version at the pre-push checkpoint — bumps the code version, reviews README/CLAUDE.md drift (skippable via `--skip-docs`), dispatches `archaeologist` to synthesize edits to favorited (`favorite: true`) north-star docs against the version brief, deletes the brief on apply, and packages KB writes + code edits in a single commit (it never pushes). The version brief is one KB doc per version, owned by `/design` and deleted by `/ship` because git history is the historical record; the north star is whatever docs the user marks `favorite: true`. Skills resolve the active project via inference (explicit arg → `.tab-project` file → git remote → cwd → recent activity) and respect a shared task-readiness bar.
- **tab-cli** (Python package, `cli/`) runs the markdown substrate outside Claude Code. Typer for the verb-shaped CLI surface (`tab ask`, `tab chat`, `tab <skill>`, `tab mcp`, `tab setup`); pydantic-ai for the agent loop and tool dispatch; grimoire for semantic-gate routing of user input against skill descriptions with per-skill thresholds. Two backends: `anthropic:<model>` via pydantic-ai's stock `AnthropicModel`, and `ollama:<model>` via Tab's in-house `OllamaNativeModel` (talks to Ollama's `/api/chat` directly, sidestepping pydantic-ai's stock `OllamaModel` which routes through the `/v1` OpenAI-compat layer). v0 ports the `tab/` plugin's personality skills (`draw-dino`, `listen`, `think`, `teach`); the `tab-for-projects` skills stay Claude-Code-shaped because they're tightly coupled to the MCP and the subagent dispatch primitive. The CLI reads its substrate from `plugins/tab/` so the markdown stays singular. `tab mcp` exposes the CLI as an MCP server for any MCP-aware host (including Claude Code) to call.
- Each Claude Code plugin is independently installable. A `settings.json` at a package root can set the default agent via `{"agent": "<plugin>:<agent>"}`. The CLI installs separately via `uv sync` inside `cli/`.

## Conventions

**Agents** are markdown files with YAML frontmatter (`name`, `description`). The body is the system prompt. Registered in `plugin.json` under `"agents"` as relative paths.

**Skills** live in `skills/<skill-name>/SKILL.md`. The body defines behavior, trigger rules, and output format. Registered in `plugin.json` via `"skills": "./skills/"` (directory reference). Skill frontmatter fields:

- `name` -- skill identifier, lowercase with hyphens, matches directory name. Parsed by the runtime.
- `description` -- what the skill does; the runtime uses this for trigger matching and catalog display. Parsed by the runtime.
- `argument-hint` -- (optional) pattern showing expected arguments (e.g., `"[topic]"`, `"<project ID>"`). Not parsed by the runtime, but useful as a quick-glance convention.

No other frontmatter fields should be added. Information about which agents run a skill, what mode it operates in, or what MCP servers it requires belongs in the skill body, not the frontmatter — duplicating it in YAML creates a maintenance trap and looks load-bearing when it isn't.

**Plugin metadata** lives in `plugins/<package>/.claude-plugin/plugin.json` with fields: `name`, `description`, `version`, `author`, `license`, `agents` (array of paths), `skills` (directory path).

**Marketplace manifest** at `.claude-plugin/marketplace.json` lists all plugins with `name`, `source`, `description`, `version`, `strict`.

**CLI package** lives in `cli/` with standard Python conventions: `pyproject.toml`, `src/tab_cli/`, `tests/`. The CLI reads markdown from `plugins/tab/` rather than duplicating it — the substrate stays singular across runtimes. CLI work runs from `cli/` (`uv sync`, `uv run tab`, `uv run pytest`).

## Validation

Run `bash scripts/validate-plugins.sh` from the repo root after any structural change — adding/removing skills, agents, or updating plugin metadata. It checks:

- Agent and skill paths resolve correctly
- Frontmatter is valid
- Versions are in sync between marketplace and plugin.json
- CLAUDE.md structure tree matches what's actually on disk

If you add or remove a skill/agent, update the Repository Structure tree above and run the validator. It will fail if the tree is out of date.

## Versioning

Bump the version in both `plugin.json` and `marketplace.json` as part of any commit that changes a plugin's behavior — new skills, agent prompt changes, bug fixes. The validator enforces that versions stay in sync across the two files, so always update both together.

The CLI versions independently in `cli/pyproject.toml`. It's not in the marketplace, so the validator doesn't touch it.

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
| `plugins/tab/.claude-plugin/plugin.json` | Tab plugin manifest |
| `plugins/tab-for-projects/.claude-plugin/plugin.json` | Tab for Projects plugin manifest |
| `plugins/tab/agents/tab.md` | Tab agent — personality, profiles, settings |
| `plugins/tab-for-projects/agents/advocate.md` | Advocate subagent — adversarial position-defender; takes an assigned position + archaeologist report + design question, returns the strongest case with file/line and doc/passage anchors; explicitly non-neutral; dispatched by `/design` in parallel after `archaeologist` runs on contested decisions; no KB writes, no code edits |
| `plugins/tab-for-projects/agents/archaeologist.md` | Archaeologist subagent — three caller modes: autonomous design synthesis closing design tasks (for `/develop`), research briefer ahead of human-hosted `/design` conversations, and north-star synthesis proposing edits to favorited docs against a version brief (for `/ship`); never writes KB docs, never edits code |
| `plugins/tab-for-projects/agents/developer.md` | Developer subagent — worktree-only; writes code + tests atomically; commits in the worktree; never merges; called by `/develop` |
| `plugins/tab-for-projects/agents/project-planner.md` | Project-planner subagent — expert codebase reader; called by `/design` (after the brief) and `/curate` (slotting loose inbox work into an in-progress version); creates tasks for uncaptured work, grooms below-bar tasks to the quality bar for their effort, searches the KB, reads the codebase; falls back to design tickets for forks it can't resolve; never writes KB docs, never edits code |
| `plugins/tab-for-projects/agents/bug-hunter.md` | Bug-hunter subagent — targeted investigation returning a structured report with file + line anchors and explicit confidence levels; called by `/design` (runtime forks), `/qa` (runtime side of a version audit), or directly; does not edit code or touch the backlog |
| `plugins/tab-for-projects/skills/jot/SKILL.md` | `/jot` — one-shot capture into the reserved inbox `group_key="new"`; title required (synthesized silently from the prior utterance when omitted), optional summary/category; never asks follow-up questions; no codebase/KB reads; no planner dispatch |
| `plugins/tab-for-projects/skills/curate/SKILL.md` | `/curate` — manual-only inbox drain; pulls `group_key="new"` plus other loose tasks, dispatches `project-planner` to groom each candidate as it slots into an existing in-progress version; target group inferred when exactly one version is in progress; `--dry-run` prints the slate without writing; cannot open new versions (refers user to `/design`); cannot write KB; no other skill suggests it |
| `plugins/tab-for-projects/skills/design/SKILL.md` | `/design` — version-anchored conversational KB authorship; commits to a version on entry (open new or extend in-progress) and announces the pick + goal, draws out one goal as the filter, dispatches `archaeologist` for evidence then `advocate` agents in parallel on contested decisions; pre-dispatch preview shows brief + version slug + task fan-out and applies (interrupt to redirect); `--dry-run` stops after preview; sole entry point for KB writes; only skill that opens new versions |
| `plugins/tab-for-projects/skills/discuss/SKILL.md` | `/discuss` — pre-design scoping via multi-agent roundtable; read-only (no KB writes, no task writes, no version commitment); announces framing and proceeds; dispatches `archaeologist` once for the shared evidence base, `advocate` agents in parallel on contested direction forks, and `project-planner-as-thinker` on task-shape forks (decomposition, seams, one-ticket-or-three); `bug-hunter` subs in when the question is a runtime concern in design clothing; closes with a recommendation (`/design`, `/jot`, done, or needs-scoping) the user invokes themselves |
| `plugins/tab-for-projects/skills/develop/SKILL.md` | `/develop` — version-anchored autopilot; takes optional `group_key` (infers the most-recently-active in-progress group when omitted; refuses `"new"`), reads the dependency graph, dispatches `developer` in isolated worktrees in parallel for the unblocked frontier, FF-merges the first returning dev / --no-ff for the second-and-later, halts on dirty tree / three consecutive failures / merge content conflict / user interrupt, supports `--dry-run`, ends by suggesting `/qa <group_key>` |
| `plugins/tab-for-projects/skills/qa/SKILL.md` | `/qa` — version audit orchestrator; takes optional `group_key` (infers the most-recently-active in-progress group when omitted; refuses `"new"`), dispatches `bug-hunter` (runtime) and `archaeologist` (alignment) in parallel, files concrete gap tasks into the same group, surfaces complexity/risk for the user without auto-filing design tasks |
| `plugins/tab-for-projects/skills/ship/SKILL.md` | `/ship` — pre-push sweep capping a version; bumps the code version, reviews README/CLAUDE.md drift (skippable via `--skip-docs`), dispatches `archaeologist` to synthesize edits to favorited (`favorite: true`) north-star docs against the version brief, deletes the brief, prints the full preview then applies (`--dry-run` stops after preview), packages KB writes + code edits in a single commit; does not push |
| `plugins/tab-for-projects/skills/search/SKILL.md` | `/search` — find docs and tasks via an escalating filter ladder |
| `plugins/tab/settings.json` | Tab default agent config |
| `cli/pyproject.toml` | Tab CLI package metadata; entry point `tab` -> `tab_cli.cli:app` |
| `cli/src/tab_cli/cli.py` | Typer app — verb-shaped subcommands (`ask`, `chat`, `<skill>`, `mcp`, `setup`); bare `tab` defaults to `chat` |
| `cli/src/tab_cli/personality.py` | Compiles `plugins/tab/agents/tab.md` (body + 0-100% settings frontmatter) into a pydantic-ai system prompt |
| `cli/src/tab_cli/registry.py` | Skill registry — parses SKILL.md descriptions for grimoire's semantic-gate routing |
| `cli/src/tab_cli/mcp_server.py` | `tab mcp` runtime — exposes the CLI as an MCP server for any MCP-aware host |
| `cli/src/tab_cli/models/ollama_native.py` | `OllamaNativeModel` — pydantic-ai `Model` subclass backed by `ollama-python`'s `/api/chat`; bypasses pydantic-ai's stock `OllamaModel` which routes through the `/v1` OpenAI-compat layer |
