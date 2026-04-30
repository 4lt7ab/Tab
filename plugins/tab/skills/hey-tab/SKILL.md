---
name: hey-tab
description: "Print setup instructions for MCPs that Tab uses. Use when the user invokes /hey-tab."
---

# Hey Tab

Prints the exact commands a user needs to run to configure MCPs that Tab works well with. No magic — just copy-paste-ready `claude mcp add` one-liners.

## Trigger

**When to activate:**
- User invokes `/hey-tab`

**When NOT to activate:**
- User asks about Tab's capabilities or features → just answer directly
- User asks how to configure MCPs in general → that's a different conversation

## Behavior

When the user runs `/hey-tab`, print the following block exactly:

---

> Tab also runs as a standalone CLI with multi-provider support
> (Anthropic / OpenAI / Google / Groq / Ollama). For CLI install
> and provider keys, run `tab setup` after installing via
> `uv tool install tab`.

**MCPs that Tab likes to use:**

These are optional — Tab works fine without them. But they unlock web search, research, and fetching capabilities that make several skills (like `/teach`) significantly better.

### Exa

Web search and content fetching. Used by `/teach` — degrades gracefully without it.

```bash
claude mcp add --scope user --transport http exa https://mcp.exa.ai/mcp
```

**Working with Tab:**

Tab's personality has dials you can turn — humor, directness, warmth, autonomy, verbosity. Adjust them on the fly:

- *"set humor to 90%"* — more wordplay
- *"be more direct"* — raise directness
- *"set autonomy to 80%"* — Tab acts on clear signals without asking first
- *"be more terse"* — drop verbosity

Changes persist for the session.

---

That's it. Print the block above and nothing else. Don't paraphrase, don't add commentary, don't offer to run the commands.

## Constraints

- **Print exactly.** No rewording, no additional context, no offers to help.
- **One and done.** The skill completes after printing the block. No follow-up.
