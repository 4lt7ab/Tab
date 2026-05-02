# Setup

**TL;DR:** Two ways to run Tab — install the Claude Code plugin (consumer path) or run the CLI from a clone (dev path). Both read the same markdown substrate.

**When to read this:** First time on the repo, or first time installing Tab as a user.

---

## Prerequisites

- **Python** `>=3.12,<3.13` (see `cli/pyproject.toml`).
- **uv** — Python package manager. Tool versions are pinned in `.tool-versions` (`uv`, `just`).
- **just** — task runner. `just --list` shows the recipes.

## Install as a Claude Code plugin

```
claude plugin add --from "https://github.com/4lt7ab/Tab" tab
```

The marketplace manifest at `.claude-plugin/marketplace.json` defines the plugin; Claude Code resolves it from this repo at the tagged ref.

## Run the CLI from a clone

```bash
cd cli
uv sync
uv run tab --help
```

The CLI is verb-shaped:

```bash
# One-shot
uv run tab ask --model 'anthropic:claude-sonnet-4-5' "what's a good way to think about premature abstraction?"
uv run tab ask --model 'ollama:gemma3:latest' "..."

# Interactive REPL (default when invoked with no subcommand)
uv run tab chat --model 'anthropic:claude-sonnet-4-5'

# One-shot skill verb
uv run tab draw-dino "stegosaurus, please"

# Multi-turn skills (listen, think, teach, cairn) live inside `tab chat` —
# grimoire routes phrases like "teach me about CRDTs" to the right skill.
uv run tab chat
```

From the repo root, `just tab <args>` is equivalent to `cd cli && uv run tab <args>`.

## Personality dials

`--humor`, `--directness`, `--warmth`, `--autonomy`, `--verbosity` accept ints 0–100 and apply to any subcommand. Layering precedence: flag > `~/.tab/config.toml` > `tab.md` defaults.

`~/.tab/config.toml` also holds the default model identifier so bare `tab` works without `--model`:

```toml
[model]
default = "anthropic:claude-sonnet-4-5"  # or "ollama:gemma3:latest"

[settings]
humor = 65
directness = 80
```

## Provider keys

pydantic-ai picks these up from the environment:

```bash
export ANTHROPIC_API_KEY=...
export OPENAI_API_KEY=...
export GEMINI_API_KEY=...
export GROQ_API_KEY=...
```

Ollama needs no key — point at `OLLAMA_HOST` if running remote. `uv run tab setup` prints these hints inline.
