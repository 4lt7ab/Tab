# Decisions

**TL;DR:** Choices we deliberately made, and choices we explicitly rejected. Mostly the rejections — they're the ones that look tempting from the outside.

**When to read this:** When tempted to "simplify" something that looks dead, or before reviving a feature that was previously cut.

---

## Things we rejected

### `tab mcp` subcommand (CLI-as-MCP-server)

Retired 0.4.0, zero callers. Resurrection is cheap when a real host wires up.

### pydantic-ai's stock `OllamaModel`

Routes through the OpenAI-compat `/v1` layer and loses features (model-registration drift on some installs, missing fields). The in-house `OllamaNativeModel` (`cli/src/tab_cli/models/ollama_native.py`) talks to `/api/chat` directly. **Don't "simplify" by switching back.**

### Frontmatter for "which agent runs this skill" or "what mode it operates in"

Duplicates the body, creates a maintenance trap, looks load-bearing when it isn't. Skill frontmatter is `name`, `description`, optional `argument-hint`. Everything else lives in the body.

### Duplicating a `SKILL.md` into both homes

A skill lives in exactly one place. CLI-only capability → `cli/src/tab_cli/skills/`; portable substrate → `plugins/tab/skills/`. The registry loader rejects a `name` that appears in both, on purpose.

### Multi-turn skills as one-shot Typer verbs

`listen`, `think`, `teach` used to ship as one-shot verbs. A single turn produced only the SKILL body's first move (a "listening, say done" line; a single shaping question; a Phase 1 calibration), and the docstring had to direct the user to `tab chat` anyway. The verbs were cut. The skills stay on the substrate; grimoire inside `tab chat` routes to them.

A one-shot verb earns its keep only when the SKILL body actually finishes in one turn. `draw-dino` does. Conversation-shaped skills do not.
