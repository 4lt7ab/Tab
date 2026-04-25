# tab-cli

The Tab CLI — a verb-shaped agent that runs the Tab personality and skills outside Claude Code.

This package is the v0 skeleton. Subcommands and agent wiring land in their own tickets.

## Usage

```bash
cd cli
uv sync
uv run tab --help
```

## Layout

```
cli/
  pyproject.toml
  src/tab_cli/
    __init__.py
    __main__.py     # python -m tab_cli
    cli.py          # Typer app
  tests/
    test_smoke.py
```

## Stack

- **Typer** — CLI surface (verb-shaped subcommands, REPL, MCP server mode).
- **pydantic-ai** — agent loop, provider abstraction, tool dispatch, structured output.
- **grimoire** (tag-pinned) — semantic-gate routing of user input against skill/tool descriptions.

See KB doc `01KQ2YKTWGXQKYZZS56Y29KT0C` for the full decision context.
