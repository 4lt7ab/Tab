# Tab

Personality, workflows, and skills defined in plain markdown — runtimes are interchangeable.

Two runtimes live here:

- **Claude Code plugins** under `plugins/`: **tab** (a standalone personality/thinking-partner agent) and **tab-for-projects** (autonomous subagents and workflow skills that talk to the Tab for Projects MCP). Published via `.claude-plugin/marketplace.json`.
- **Tab CLI** under `cli/`: a Python package (`tab`) that runs the same markdown substrate outside Claude Code — multi-provider via pydantic-ai, semantic-gated skill routing via grimoire.

The markdown is the source of truth; the runtimes read it.

## Repository Structure

```
.claude-plugin/marketplace.json     # Marketplace manifest — lists both plugins
README.md                           # Project README
LICENSE                             # Apache-2.0 license
scripts/validate-plugins.sh         # Plugin validation script
cli/                                # Tab CLI — Python runtime for the markdown substrate
  pyproject.toml                    #   Package metadata; entry point: `tab` -> tab_cli.cli:app
  src/tab_cli/                      #   Typer app, personality compiler, grimoire registry, Ollama-native model
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
    agents/archaeologist.md         #   Archaeologist advisor — grounds in code + KB, prescribes a concrete solution and names which KB docs apply and how; read-only (no KB writes, no code edits, no task mutations)
    agents/code-reviewer.md         #   Code-reviewer advisor — reviews code since the last major release through a prompt-supplied angle, grounds in code + KB, returns an issues report with type / how_found / impact / difficulty / fix_direction / fail-forward call (ship-blocker | ship-with-followup | next-cycle | accept); read-only (no code edits, no KB writes, no task mutations)
    agents/product-researcher.md    #   Product-researcher advisor — the only advisor allowed to look outside the project, reaching the open web via Exa for libraries, patterns, and prior art; KB-first, cross-checks every external claim against the KB and cites url + fetched_at + verbatim quote; read-only (no KB writes, no code edits, no task mutations)
    agents/project-planner.md       #   Project-planner advisor — grounds in code + KB + current backlog, prescribes which tasks to create or update with effort + impact + edges; read-only (no task writes, no KB writes, no code edits)
    skills/discuss/SKILL.md         #   /discuss — agent-driven planning; runs the core advisors (archaeologist, project-planner, code-reviewer) in parallel against a goal — adding product-researcher when the goal calls for outside evidence — then cross-questions them across rounds until forks collapse, returning one synthesized project plan with very few decisions left for the human; read-only (no MCP / code / KB writes); the user (or a future writer) commits the plan to the backlog
    skills/grind/SKILL.md           #   /grind — autonomous implementation against a grouped backlog; refuses without a group_key (and refuses "new"), reads the dependency graph, dispatches general-purpose agents in isolated worktrees on the unblocked frontier (parallel when surfaces don't conflict), calls archaeologist / project-planner when judgment is needed and writes the prescribed task/edge updates to the MCP itself, halts on dirty tree / three consecutive failures / merge conflict / user interrupt / group done; supports --dry-run
```

## Package Architecture

Two Claude Code plugins (`plugins/tab`, `plugins/tab-for-projects`) and one Python runtime (`cli/`). All three sit on the same markdown substrate — `agents/*.md` and `skills/*/SKILL.md` under `plugins/tab/` — so personality and skill changes flow to whichever runtime loads them.

- **tab** (Claude Code plugin) is standalone. One agent (`Tab`) with a rich personality system (profiles, settings 0-100%). No MCP dependency.
- **tab-for-projects** (Claude Code plugin) is deliberately small: four read-only advisor subagents (`archaeologist`, `project-planner`, `code-reviewer`, `product-researcher`) and two skills (`/discuss`, `/grind`) against the Tab for Projects MCP. `/discuss` is read-only synthesis: it runs the core advisors (`archaeologist`, `project-planner`, `code-reviewer`) in parallel against a goal — adding `product-researcher` when the goal calls for outside evidence — then cross-questions them across rounds until forks collapse into one converged plan with very few decisions left for the human; the user commits the plan to the backlog (via the MCP directly) when they're ready. `/grind` executes a group. The advisors never write — they ground themselves in the project's code, KB, and (for the planner) backlog, then prescribe a concrete solution. The archaeologist prescribes what to do and which KB docs apply and how; the project-planner prescribes which tasks to create or update with effort, impact, and the dependency edges that connect them; the code-reviewer reviews code since the last major release through a prompt-supplied angle and returns an issues report with type, evidence, impact, difficulty, fix direction, and a fail-forward call (ship-blocker | ship-with-followup | next-cycle | accept) — calibrated to ship early and often, with a high bar for blocking releases; the product-researcher is the only advisor allowed to look outside the project, reaching the open web via Exa for libraries, patterns, and prior art, KB-first and cross-checking every external claim against the project's own decisions before recommending. `/grind` is the execution writer: it takes a `group_key` (refuses without one, refuses `"new"`), reads the dependency graph, and dispatches Claude Code's built-in `general-purpose` agent in isolated git worktrees against the unblocked frontier — in parallel when the planner has confirmed surfaces don't conflict. As work returns, `/grind` fast-forward-merges the first dev of a parallel batch, `--no-ff`-merges the second-and-later, and writes task status (and any advisor-prescribed task/edge updates) back to the MCP. It calls the advisors when judgment is required — fuzzy task body, design-category fork, surprise from a returning agent — and writes their prescriptions itself; advisors don't write, the skill does. `/grind` halts on a dirty tree, three consecutive failures, a merge content conflict, a user interrupt, or group done, and supports `--dry-run` to preview the first round without writing. There is no inbox capture, no version anchoring, no pre-push sweep — those exist if you need them by talking to the MCP directly; the slimmer surface lets real gaps emerge naturally.
- **tab-cli** (Python package, `cli/`) runs the markdown substrate outside Claude Code. Typer for the verb-shaped CLI surface (`tab ask`, `tab chat`, `tab <skill>`, `tab setup`); pydantic-ai for the agent loop and tool dispatch; grimoire for semantic-gate routing of user input against skill descriptions with per-skill thresholds. Two backends: `anthropic:<model>` via pydantic-ai's stock `AnthropicModel`, and `ollama:<model>` via Tab's in-house `OllamaNativeModel` (talks to Ollama's `/api/chat` directly, sidestepping pydantic-ai's stock `OllamaModel` which routes through the `/v1` OpenAI-compat layer). v0 ports the `tab/` plugin's personality skills (`draw-dino`, `listen`, `think`, `teach`); the `tab-for-projects` skills stay Claude-Code-shaped because they're tightly coupled to the MCP and the subagent dispatch primitive. The CLI reads its substrate from `plugins/tab/` so the markdown stays singular. (An earlier `tab mcp` subcommand exposed the CLI as an MCP server but had zero callers; it was retired in 0.4.0 — resurrection is cheap when a real host wires up.)
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

The tree check is deliberately soft: the validator only greps for substring presence of each skill/agent path somewhere in CLAUDE.md. Tree-art whitespace, indentation, and box-drawing characters are decorative — adding or removing a skill doesn't require redrawing the ASCII tree, just making sure the path string appears in the file. The guarantee is that on-disk-but-not-mentioned trips the validator; cosmetic surgery isn't part of the contract.

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
| `plugins/tab-for-projects/agents/archaeologist.md` | Archaeologist advisor — grounds in code + KB, prescribes a concrete solution and names which KB docs apply and how; read-only (no KB writes, no code edits, no task mutations) |
| `plugins/tab-for-projects/agents/code-reviewer.md` | Code-reviewer advisor — reviews code since the last major release through a prompt-supplied angle, grounds in code + KB, returns an issues report with type / how_found / impact / difficulty / fix_direction / fail-forward call (ship-blocker \| ship-with-followup \| next-cycle \| accept); read-only (no code edits, no KB writes, no task mutations) |
| `plugins/tab-for-projects/agents/product-researcher.md` | Product-researcher advisor — the only advisor allowed to look outside the project, reaching the open web via Exa for libraries, patterns, and prior art; KB-first, cross-checks every external claim against the KB and cites url + fetched_at + verbatim quote; read-only (no KB writes, no code edits, no task mutations) |
| `plugins/tab-for-projects/agents/project-planner.md` | Project-planner advisor — grounds in code + KB + current backlog, prescribes which tasks to create or update with effort + impact + edges; read-only (no task writes, no KB writes, no code edits) |
| `plugins/tab-for-projects/skills/discuss/SKILL.md` | `/discuss` — agent-driven planning; runs the core advisors (`archaeologist`, `project-planner`, `code-reviewer`) in parallel against a goal — adding `product-researcher` when the goal calls for outside evidence — then cross-questions them across rounds until forks collapse, returning one synthesized project plan with very few decisions left for the human; read-only (no MCP / code / KB writes); the user commits the plan to the backlog when ready |
| `plugins/tab-for-projects/skills/grind/SKILL.md` | `/grind` — autonomous implementation against a grouped backlog; refuses without a `group_key` (and refuses `"new"`), reads the dependency graph, dispatches `general-purpose` agents in isolated worktrees on the unblocked frontier (parallel when surfaces don't conflict), calls `archaeologist` / `project-planner` when judgment is needed and writes the prescribed task/edge updates to the MCP itself, halts on dirty tree / three consecutive failures / merge conflict / user interrupt / group done; supports `--dry-run` |
| `plugins/tab/settings.json` | Tab default agent config |
| `cli/pyproject.toml` | Tab CLI package metadata; entry point `tab` -> `tab_cli.cli:app` |
| `cli/MAINTENANCE.md` | CLI runtime conventions — lazy imports, test seams, `tab: <reason>` error pattern, substrate-singular rule |
| `cli/src/tab_cli/cli.py` | Typer app — verb-shaped subcommands (`ask`, `chat`, `<skill>`, `setup`); bare `tab` defaults to `chat` |
| `cli/src/tab_cli/commands.py` | Shared subcommand scaffolding — `@personality_command` decorator, `TabContext` resolved bundle, dial/model Options, `tab: <reason>` error wrapper |
| `cli/src/tab_cli/grimoire_cli.py` | `tab grimoire` subcommand group — `set` / `reset` / `show` for per-skill threshold overrides |
| `cli/src/tab_cli/personality.py` | Compiles `plugins/tab/agents/tab.md` (body + 0-100% settings frontmatter) into a pydantic-ai system prompt |
| `cli/src/tab_cli/registry.py` | Skill registry — parses SKILL.md descriptions for grimoire's semantic-gate routing |
| `cli/src/tab_cli/models/ollama_native.py` | `OllamaNativeModel` — pydantic-ai `Model` subclass backed by `ollama-python`'s `/api/chat`; bypasses pydantic-ai's stock `OllamaModel` which routes through the `/v1` OpenAI-compat layer |
