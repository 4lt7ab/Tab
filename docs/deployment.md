# Deployment

**TL;DR:** One bump command moves all four version files in lockstep. Two distribution channels: the Claude Code plugin via git tag, the CLI to PyPI.

**When to read this:** Cutting a release.

---

## Versions

Everything in this repo is pinned at a single version. Four files carry it and they all move together:

- `.claude-plugin/marketplace.json` (`plugins[0].version`)
- `plugins/tab/.claude-plugin/plugin.json` (`version`)
- `cli/pyproject.toml` (`[project].version`)
- `cli/uv.lock` (follows from `uv sync`)

**The only blessed way to change a version is `just bump`.** Bare `just bump` increments the patch (`0.0.1 → 0.0.2`); pass an explicit semver to override (`just bump 1.0.0`). The recipe rewrites all four files, runs `just validate`, and runs `just test`.

Versions are a release signal, not a side effect of editing code. Do not edit any `version` field by hand. Do not bundle a bump into an unrelated change. If a task seems to need a version bump, surface it in the response and stop — the human decides when to run the recipe. (See `.claude/rules/never-bump-versions.md`.)

## Release process

One command, two channels:

1. `just bump` — patch bump (or `just bump <x.y.z>` for an explicit version). Rewrites all four files, runs `just validate`, runs `just test`.
2. Commit.
3. **Plugin:** tag `tab-<x.y.z>` and push. The marketplace resolves from the repo at the tagged ref.
4. **CLI to PyPI:** tag `v<x.y.z>`, then `cd cli && uv build && uv publish`.

PyPI distribution name is `tab`; the importable Python package is still `tab_cli`. The split is intentional, like `pip install Pillow → import PIL`.
