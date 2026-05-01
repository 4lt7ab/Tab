# Tab

Personality, workflows, and skills as plain markdown — runtimes are interchangeable. A Claude Code plugin (`plugins/tab/`) and a Python runtime (`cli/`) both read the same substrate. The markdown is the source of truth; the runtimes read it.

## Architecture seams

- **Substrate is singular.** `plugins/tab/` is canonical. The CLI reads SKILL.md / agent.md straight out of the plugin tree via `cli/src/tab_cli/paths.py:plugins_dir()`. No copy, no vendored markdown, no `cli/skills/`. If you're tempted to duplicate, stop.
- **Plugin registration.** `plugins/<pkg>/.claude-plugin/plugin.json` carries `name`, `description`, `version`, `agents` (path array), `skills` (directory ref). Versions in `marketplace.json` and each `plugin.json` must match — the validator enforces this.

## Conventions

- **Skill frontmatter: `name`, `description`, optional `argument-hint`. No other fields.** Behavior, owning agents, MCP requirements go in the body. Extra frontmatter looks load-bearing, isn't, and rots.
- **Agent frontmatter: `name`, `description`.** Body is the system prompt.
- **CLI subcommands lazy-import** their runners so `tab --help` and unrelated paths don't pay pydantic-ai's import cost. `cli/MAINTENANCE.md` is the canonical reference for CLI shape.
- **CLI runtime errors** collapse to a single stderr line of the form `tab: <reason>`, exit non-zero, never spill a traceback. New subcommand → wrap the runner the same way.
- **CLI work runs from `cli/`**: `uv sync`, `uv run tab`, `uv run pytest`.

## Decisions we rejected

- **`tab mcp` subcommand** (CLI-as-MCP-server) — retired 0.4.0, zero callers. Resurrection is cheap when a real host wires up.
- **pydantic-ai's stock `OllamaModel`** — routes through the OpenAI-compat `/v1` layer and loses features. The in-house `OllamaNativeModel` talks to `/api/chat` directly. Don't "simplify" by switching.
- **Frontmatter for "which agent runs this skill" or "what mode it operates in"** — duplicates the body, creates a maintenance trap, looks load-bearing when it isn't.
- **Copying markdown into the CLI** — the substrate stays in `plugins/tab/`. Every `paths.plugins_dir()` call exists to enforce this.

## Gotchas

- **The validator's tree check is soft — substring presence only.** Tree-art whitespace, indentation, and box-drawing characters are decorative. Don't repair tree art; just make sure each path under "Key paths" below stays in the file.
- **Skill behavior lives in SKILL.md, not here.** Don't paraphrase skill behavior in CLAUDE.md — the SKILL.md body is canonical, and a recap here bit-rots the moment behavior shifts.
- **`personality.py` imports `pydantic_ai.Agent` at module top.** That's why every other subcommand defers `tab_cli.personality` — deferring the module is what defers pydantic-ai's import cost.

## Commit messages

Short. Wordplay over summary. The diff says *what* changed — the subject is flavor, not a recap. Riff on the code: a pun, a callback, a phrase that fits. Under ~40 chars. Drop conventional-commit prefixes unless part of the joke.

Recent calibration: `one-shot or it isn't a verb`, `commit checks in`, `the advisor council adjourns`, `the briefing earns its rent`, `the suite admits a third`.

## Validation

`bash scripts/validate-plugins.sh` from the repo root, after any structural change — adding/removing skills, agents, bumping versions, editing plugin metadata. The script checks frontmatter, version sync between `marketplace.json` and each `plugin.json`, and the soft tree check above.

## Key paths

Manifests:

- `.claude-plugin/marketplace.json`
- `plugins/tab/.claude-plugin/plugin.json`
- `plugins/tab/settings.json` — default agent for the `tab` plugin

Substrate (validator-required: every path below must appear somewhere in this file):

- `plugins/tab/agents/tab.md` — personality agent (profiles, 0-100% settings)
- `plugins/tab/skills/draw-dino/SKILL.md`
- `plugins/tab/skills/hey-tab/SKILL.md`
- `plugins/tab/skills/listen/SKILL.md`
- `plugins/tab/skills/teach/SKILL.md`
- `plugins/tab/skills/think/SKILL.md`

CLI runtime (read `cli/MAINTENANCE.md` before editing):

- `cli/pyproject.toml` — entry point `tab` → `tab_cli.cli:app`
- `cli/src/tab_cli/cli.py` — Typer app; verb-shaped subcommands
- `cli/src/tab_cli/paths.py` — `plugins_dir()`, substrate-singular helper
- `cli/src/tab_cli/personality.py` — pydantic-ai compile site
- `cli/src/tab_cli/registry.py` — semantic-gate skill routing
- `cli/src/tab_cli/models/ollama_native.py` — `/api/chat` backend

Validation:

- `scripts/validate-plugins.sh`
