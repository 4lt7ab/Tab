# tab-cli

The Tab CLI — a verb-shaped agent that runs the Tab personality and skills outside Claude Code.

The personality and skills live as plain markdown in `../plugins/tab/`. This package compiles them into a pydantic-ai agent and routes input through grimoire to decide whether the user invoked a skill or wants the agent.

## Usage

```bash
cd cli
uv sync
uv run tab --help

# One-shot
uv run tab ask --model 'anthropic:claude-sonnet-4-5' "what's a good way to think about premature abstraction?"
uv run tab ask --model 'ollama:gemma3:latest' "..."

# Interactive REPL (default when invoked with no subcommand)
uv run tab chat --model 'anthropic:claude-sonnet-4-5'

# Skills directly
uv run tab draw-dino "stegosaurus, please"
uv run tab teach "byzantine fault tolerance"
uv run tab listen
uv run tab think

# Setup hints
uv run tab setup
```

Personality dials (`--humor`, `--directness`, `--warmth`, `--autonomy`, `--verbosity`) accept ints in 0-100 and apply to any subcommand. Layering: flag > `~/.tab/config.toml` > `tab.md` defaults.

`~/.tab/config.toml` also holds the default model identifier so bare `tab` works without `--model`:

```toml
[model]
default = "anthropic:claude-sonnet-4-5"  # or "ollama:gemma4:latest"

[settings]
humor = 65
directness = 80
```

## Layout

```
cli/
  pyproject.toml           # Package metadata; entry point: `tab` -> tab_cli.cli:app
  src/tab_cli/
    __init__.py
    __main__.py            # python -m tab_cli
    cli.py                 # Typer app; verb-shaped subcommands
    personality.py         # Compiles plugins/tab/agents/tab.md into a pydantic-ai Agent
    config.py              # Reads ~/.tab/config.toml for [model].default + personality dials
    chat.py                # tab chat REPL with sticky-skill mode and history threading
    skills.py              # Shared skill runner (read SKILL.md body + compile skill agent)
    registry.py            # SKILL.md loader: seeds grimoire's Gate for semantic routing
    grimoire_overrides.py  # `tab grimoire` per-skill threshold persistence
    web_search.py          # Exa-backed web_search tool for /teach
    setup.py + setup.md    # `tab setup` body and command
    models/
      ollama_native.py     # pydantic-ai Model backed by ollama-python's /api/chat
  tests/
    fixtures/
      dispatch_eval.json   # Skill-dispatch eval cases for grimoire calibration
    test_*.py              # ~12 test files; uv run pytest from cli/
```

## Stack

- **Typer** — CLI surface (verb-shaped subcommands, REPL).
- **pydantic-ai** — agent loop, tool dispatch, structured output.
- **anthropic** — first backend (`anthropic:<model>`) via pydantic-ai's stock `AnthropicModel`.
- **ollama-python** — second backend (`ollama:<model>`) via Tab's in-house `OllamaNativeModel`, which talks to `/api/chat` directly. pydantic-ai's stock `OllamaModel` extends `OpenAIChatModel` and routes through `/v1` OpenAI-compat, which has model-registration drift on some installs.
- **grimoire** (tag-pinned) — semantic-gate routing of user input against skill descriptions.

See KB doc `01KQ2YKTWGXQKYZZS56Y29KT0C` for the architectural decision context.
