# Never bump versions

**When this applies:** Any change that would touch a `version` field anywhere in the repo.

Don't. The four version-carrying files (`marketplace.json`, `plugins/tab/.claude-plugin/plugin.json`, `cli/pyproject.toml`, `cli/uv.lock`) move only via `just bump`. The recipe rewrites all four in lockstep and re-runs `just validate` and `just test`.

Don't propose a bump as part of an unrelated change. Don't edit a `version` line by hand. If a task seems to need a version bump, surface it in the response and stop — the human decides when to run the recipe.

Versions are a release signal, not a side effect of editing code. See [docs/deployment.md](../../docs/deployment.md).
