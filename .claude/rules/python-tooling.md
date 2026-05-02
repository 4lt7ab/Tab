# Python tooling

**When this applies:** Running anything Python-shaped in this repo.

Use `uv`. Never call `pip`, `python -m pip`, or `python3` directly.

CLI work runs from `cli/`:

```bash
cd cli
uv sync           # sync the venv from the lockfile
uv run tab        # run the CLI entry point
uv run pytest     # tests
```

From the repo root, `just tab <args>` is equivalent to `cd cli && uv run tab <args>`. Prefer `just` recipes (`just test`, `just validate`, `just sync`) over ad-hoc commands.
