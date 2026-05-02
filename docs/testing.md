# Testing

**TL;DR:** `just test` runs pytest from `cli/`. It is the only blocking gate before commit. `just validate` checks plugin structure separately.

**When to read this:** Writing or running tests, or before committing a structural change.

---

## Running tests

```bash
just test           # pytest from cli/ — blocking gate
just validate       # plugin frontmatter, version sync, CLAUDE.md tree check
```

Both must pass before commit. `just validate` wraps `bash scripts/validate-plugins.sh`; run it after any change to skills, agents, plugin metadata, or version.

Other recipes (`just fmt`, `just lint`, `just typecheck`) are advisory. `ruff` and `basedpyright` will flag issues but won't gate the commit.

## Where tests live

```
cli/tests/
├── fixtures/
│   └── dispatch_eval.json   # skill-dispatch eval cases for grimoire calibration
└── test_*.py
```

## Pluggable test seams

Surfaces that touch providers or disk accept a `None`-defaulted override so tests can inject a stand-in without monkeypatching imports. Example from `cli/src/tab_cli/grimoire_overrides.py`:

```python
def load_overrides(path: Path | None = None) -> dict[str, float]:
    """The optional `path` argument is a test seam; production
    callers use `overrides_path()`."""
```

The pattern: `None`-defaulted parameter wired through to the real default. Production call-sites stay untouched; tests pass a tmp path or a fake helper. When you add a new surface that touches providers or disk, follow this shape.

## What the validator checks

`scripts/validate-plugins.sh` enforces three things:

1. **Frontmatter shape.** Skills carry only `name`, `description`, optional `argument-hint`. Agents carry only `name`, `description`. The validator actively rejects extras like `mode`, `requires-mcp`, `agents`, `inputs`.
2. **Version sync.** `marketplace.json`, every `plugin.json`, and `cli/pyproject.toml` must agree.
3. **CLAUDE.md tree.** Soft substring presence — every skill `skills/<name>/SKILL.md` and every agent file must appear somewhere in CLAUDE.md. Tree-art whitespace and box-drawing characters are decorative; don't repair them.

The CLI-local skills home (`cli/src/tab_cli/skills/`) is not validated by this script; its frontmatter is checked at runtime by the registry loader instead.
