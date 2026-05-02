# Skill and agent frontmatter

**When this applies:** Writing or editing any `SKILL.md` or agent file under `plugins/tab/` or `cli/src/tab_cli/skills/`.

**Skills:** `name`, `description`, optional `argument-hint`. No other fields.

**Agents:** `name`, `description`. No other fields.

Behavior, owning agents, MCP requirements all go in the body. Extra frontmatter looks load-bearing, isn't, and rots — the validator actively rejects `mode`, `requires-mcp`, `agents`, `inputs`. If you're tempted to add a new key, write a body section instead.

Skill behavior is canonical in `SKILL.md`. Don't paraphrase it into `CLAUDE.md`, `docs/`, or anywhere else — recaps bit-rot the moment behavior shifts.
