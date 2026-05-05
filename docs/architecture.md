# Architecture

**TL;DR:** Tab is a markdown substrate (personality, skills, workflows) read by interchangeable runtimes. Today there are two: the Claude Code plugin under `plugins/tab/` and the Python CLI under `cli/`. The markdown is the source of truth; runtimes load it.

**When to read this:** Before changing how skills or agents are loaded, before adding a new runtime, or before moving anything between `plugins/tab/` and `cli/`.

---

## Repo layout

```
Tab/
├── .claude-plugin/marketplace.json   # AltTab marketplace manifest
├── plugins/tab/                      # Claude Code plugin (portable substrate)
│   ├── .claude-plugin/plugin.json    # plugin manifest — name, version, agents, skills
│   ├── settings.json                 # default agent: tab:Tab
│   ├── agents/tab.md                 # personality agent (profiles, 0–100% dials)
│   └── skills/
│       ├── draw-dino/SKILL.md
│       ├── grimoire/SKILL.md
│       ├── hey-tab/SKILL.md
│       ├── listen/SKILL.md
│       ├── teach/SKILL.md
│       └── think/SKILL.md
├── cli/                              # tab-cli — Python runtime (uv project)
│   ├── pyproject.toml                # entry: tab → tab_cli.cli:app
│   ├── MAINTENANCE.md                # canonical CLI conventions — read before editing
│   └── src/tab_cli/
│       ├── cli.py                    # Typer app; verb-shaped subcommands
│       ├── paths.py                  # plugins_dir() + cli_skills_dir()
│       ├── personality.py            # pydantic-ai compile site (heavy import)
│       ├── registry.py               # semantic-gate skill routing
│       ├── recall.py                 # multi-corpus memory tool wired into cairn
│       ├── models/ollama_native.py   # /api/chat backend (not OpenAI-compat)
│       └── skills/cairn/SKILL.md     # CLI-only memory-recall skill (grimoire-backed)
├── scripts/validate-plugins.sh       # frontmatter, version sync, CLAUDE.md tree check
├── justfile                          # task runner
└── CLAUDE.md
```

The validator walks this tree. If you move or remove a path listed under "substrate" or "CLI runtime" in CLAUDE.md, update CLAUDE.md in the same change — `validate-plugins.sh` does a soft substring presence check that will catch a missing line.

## The two skill homes

Skills live in exactly one of two places, never both:

- **`plugins/tab/skills/`** — portable substrate. Skills here ship in the Claude Code plugin and also work in the CLI. Every new skill defaults here unless it has a CLI-only dependency.
- **`cli/src/tab_cli/skills/`** — CLI-only capability. A skill goes here when it depends on something that doesn't exist in the plugin host: grimoire-core, the settings system, anything pydantic-ai-shaped. Today this directory holds `cairn` (memory recall, grimoire-backed).

The registry loader (`cli/src/tab_cli/registry.py`) walks both via `paths.plugins_dir()` and `paths.cli_skills_dir()`, merges them into one semantic gate, and rejects any `name` that appears in both sources. The CLI-local home is not part of the marketplace and is not validated by `validate-plugins.sh`; its frontmatter is checked at runtime by the registry loader instead.

## Plugin registration

`plugins/<pkg>/.claude-plugin/plugin.json` carries `name`, `description`, `version`, `agents` (path array), and `skills` (directory ref). The version in `marketplace.json` and each `plugin.json` must match — the validator enforces this.

## Key paths

Manifests:

- `.claude-plugin/marketplace.json`
- `plugins/tab/.claude-plugin/plugin.json`
- `plugins/tab/settings.json`

Substrate (validator-required — every path below must appear in CLAUDE.md):

- `plugins/tab/agents/tab.md`
- `plugins/tab/skills/draw-dino/SKILL.md`
- `plugins/tab/skills/grimoire/SKILL.md`
- `plugins/tab/skills/hey-tab/SKILL.md`
- `plugins/tab/skills/listen/SKILL.md`
- `plugins/tab/skills/teach/SKILL.md`
- `plugins/tab/skills/think/SKILL.md`

CLI runtime (read `cli/MAINTENANCE.md` before editing):

- `cli/pyproject.toml`
- `cli/src/tab_cli/cli.py`
- `cli/src/tab_cli/paths.py`
- `cli/src/tab_cli/personality.py`
- `cli/src/tab_cli/registry.py`
- `cli/src/tab_cli/recall.py`
- `cli/src/tab_cli/skills/cairn/SKILL.md`
- `cli/src/tab_cli/models/ollama_native.py`

Validation:

- `scripts/validate-plugins.sh`
