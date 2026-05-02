# Conventions

**TL;DR:** Behavior lives in the body, not the metadata. Skills and agents take minimal frontmatter. The CLI defers heavy imports per-subcommand and collapses runtime errors to one stderr line.

**When to read this:** Writing a new skill, agent, or CLI subcommand — or reviewing one. For CLI-runtime specifics, `cli/MAINTENANCE.md` is canonical.

---

## Skill and agent frontmatter

**Skill frontmatter: `name`, `description`, optional `argument-hint`. No other fields.** Behavior, owning agents, MCP requirements all go in the body. Extra frontmatter looks load-bearing, isn't, and rots. The validator actively rejects `mode`, `requires-mcp`, `agents`, `inputs`.

**Agent frontmatter: `name`, `description`.** Body is the system prompt.

Skill behavior lives in `SKILL.md`, not in `CLAUDE.md` or any other doc. Don't paraphrase it elsewhere — `SKILL.md` is canonical, and a recap bit-rots the moment behavior shifts.

## CLI conventions

The CLI has its own canonical conventions doc next to the source: `cli/MAINTENANCE.md`. Read it before editing `cli/src/tab_cli/`. Headlines:

1. **Lazy imports per subcommand.** Every Typer subcommand body lazy-imports the module it dispatches into — `tab_cli.chat`, `tab_cli.skills`, `tab_cli.personality`. `personality.py` imports `pydantic_ai.Agent` at module top, so deferring `tab_cli.personality` is what defers pydantic-ai's import cost. `tab --help` and unrelated subcommands must stay cheap and provider-free.
2. **The `tab: <reason>` stderr error pattern.** User-visible runtime failures collapse to one stderr line of the form `tab: <reason>`, exit non-zero, never spill a traceback. New subcommand → wrap the runner the same way.
3. **Pluggable test seams.** Surfaces that touch providers or disk take a `None`-defaulted override (path, helper) so tests inject without monkeypatching imports. See [testing.md](testing.md).

## Gotchas

- **The validator's tree check is soft — substring presence only.** Tree-art whitespace, indentation, and box-drawing characters are decorative. Don't repair tree art; just make sure each skill `skills/<name>/SKILL.md` and each agent `agents/<name>` stays mentioned somewhere in `CLAUDE.md`.
- **`personality.py` imports `pydantic_ai.Agent` at module top.** That's why every other subcommand defers `tab_cli.personality`. Deferring the module is what defers pydantic-ai's import cost.
