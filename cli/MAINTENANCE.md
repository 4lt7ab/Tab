# cli/ — runtime conventions

Notes for a returning agent or a future contributor about how the Tab
CLI keeps its shape. Each convention has a one-line statement, one
concrete example anchored in the current source, and a why-line if it
isn't self-evident.

## 1. Lazy imports per subcommand

Every Typer subcommand body lazy-imports the module it dispatches into
— `tab_cli.chat`, `tab_cli.skills`, `tab_cli.personality`, etc. —
instead of importing them at module top. The in-function imports live
in `cli.py` (one per dispatch site, sometimes two when a subcommand
needs both a runner and a helper).

The canonical comment names the cost being deferred. pydantic-ai is
the heavy one:

```python
# Imported lazily so `tab --help` and unrelated subcommands don't pay
# for pydantic-ai's import cost (and don't fail in environments where
# the personality file isn't reachable from cwd).
from tab_cli.personality import compile_tab_agent
```

`tab --help`, `tab grimoire show`, and other non-agent paths must stay
cheap and provider-free. `personality.py` imports `pydantic_ai.Agent`
at module top, so deferring `tab_cli.personality` is what defers
pydantic-ai.

## 2. Pluggable test seams

Surfaces that talk to providers or to disk accept a `None`-defaulted
override so tests can inject a stand-in without monkeypatching imports.

**`path` override in `grimoire_overrides`** —
`cli/src/tab_cli/grimoire_overrides.py:117` (and on `save_overrides`,
`set_override`, `reset_override`):

```python
def load_overrides(path: Path | None = None) -> dict[str, float]:
```

The docstring (`grimoire_overrides.py:128-129`) calls it out: "The
optional `path` argument is a test seam; production callers use
`overrides_path()`."

A `None`-defaulted parameter wired through to the real default keeps
production call-sites untouched while letting tests pass a tmp path or
a fake helper in.

## 3. The `tab: <reason>` stderr error pattern

User-visible runtime failures in the CLI collapse to one stderr line of
the form `tab: <reason>`, exit non-zero, and never spill a Python
traceback. Sixteen sites in `cli.py` write this exact form
(`grep 'typer.echo(f"tab: '` returns 16 hits).

The convention is documented next to its first non-trivial use,
`cli/src/tab_cli/cli.py:270-276`:

```python
except Exception as exc:  # noqa: BLE001 — surface anything as a readable error
    # Typer's default behavior on uncaught exceptions is a traceback
    # dump, which is hostile in a shell-out / CI context. We collapse
    # to a one-line stderr message and a non-zero exit so callers can
    # do the usual `|| handle` shell idiom.
    typer.echo(f"tab: {exc}", err=True)
    raise typer.Exit(code=1) from exc
```

Dial-validation errors (`_validate_dial`, `cli.py:39-53`) are the same
shape with a slightly different prefix — see the function docstring
for why we don't route through Typer's `BadParameter`. Adding a new
subcommand? Wrap the runner in this same try/except.

## 4. The CLI reads markdown in place; it does not copy

Two skill homes, one loader, no copy step, no vendored markdown.

- **`plugins/tab/`** is the portable substrate — read by both the
  Claude Code plugin host and the CLI. SKILL.md / tab.md are read
  straight out of the plugin tree.
- **`cli/src/tab_cli/skills/`** is the CLI-only skill home for skills
  whose capability depends on Python the plugin host doesn't have
  (grimoire-core, settings, pydantic-ai). Today this holds `cairn`.

`paths.py` exposes both directories. Everything routes through these
two helpers — there is no third path-derivation site:

```python
@lru_cache(maxsize=1)
def plugins_dir() -> Path:
    """Return ``<repo>/plugins`` derived from this file's location."""

@lru_cache(maxsize=1)
def cli_skills_dir() -> Path:
    """Return ``cli/src/tab_cli/skills`` — the CLI-only skill home."""
```

The registry loader (`registry.py`) walks both, merges them into one
gate, and rejects a `name` that appears in both sources. Skills shared
with the plugin host go in `plugins/tab/skills/`; CLI-only capability
goes in `cli/src/tab_cli/skills/`. Don't duplicate — the loader will
refuse to start.

If you find yourself writing `Path(__file__).resolve().parents[3]` or
re-stripping a YAML fence, stop and use `paths.py` instead — that's
the whole point of the module.

## 5. Multi-turn skills only ship as chat-routed skills

`tab draw-dino` is the only personality skill exposed as a one-shot
Typer verb. The multi-turn skills — `listen`, `think`, `teach` — used
to ship as one-shot verbs too, but a single turn produced only the
SKILL body's first move (a "listening, say done" line; a single
shaping question; a Phase 1 calibration), and the docstring had to
direct the user to `tab chat` anyway.

The verbs were cut. The skills stay on the substrate
(`plugins/tab/skills/{listen,think,teach}/SKILL.md`), and grimoire
inside `tab chat` routes to them. When adding a new skill: a one-shot
verb earns its keep only when the SKILL body actually finishes in one
turn (draw-dino does; conversation-shaped skills do not).
