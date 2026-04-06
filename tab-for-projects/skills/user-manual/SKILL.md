---
name: user-manual
description: "Unified reference for Tab for Projects — MCP tools, document discipline, prompt quality, and agent/skill authoring. Pass a keyword to load a specific reference."
argument-hint: "<mcp | documents | prompts | agents>"
---

# User Manual

A router skill that loads reference content on demand. Each reference lives in a separate file under `refs/`.

## Trigger

**When to activate:**
- The user runs `/user-manual` with or without a keyword
- An agent needs reference material for MCP tools, document conventions, prompt quality, or agent/skill authoring
- Any situation where the old `/mcp-reference`, `/document-reference`, `/prompt-reference`, or `/agentic-reference` would have activated

**When NOT to activate:**
- The user is asking about the Tab agent (standalone personality plugin) — different plugin entirely
- The user wants to create or edit a document — use the MCP tools directly

## Lookup Table

| Keyword | Aliases | File | What it covers |
|---------|---------|------|----------------|
| `mcp` | `mcp-reference`, `tools`, `data-model` | `refs/mcp.md` | MCP data model, tool signatures, usage patterns |
| `documents` | `document-reference`, `docs`, `kb` | `refs/documents.md` | Document types, create-vs-update, tagging, ownership |
| `prompts` | `prompt-reference`, `quality`, `writing` | `refs/prompts.md` | Six prompt quality rules, clarity checklist |
| `agents` | `agentic-reference`, `skills`, `authoring` | `refs/agents.md` | Agent/skill file anatomy, roles, workflows, constraints |

## Routing Protocol

**With a keyword argument:** Match the keyword against the Lookup Table (keyword or alias). Read the matching file from the `refs/` subdirectory relative to this skill's base directory using the Read tool. Print its full content. Do not summarize.

**With multiple keywords:** Load each matching reference in sequence.

**Without a keyword:** Print the Lookup Table above so the caller can choose. Do not load all references — that defeats the purpose of on-demand loading.

**Unrecognized keyword:** Print the Lookup Table and note which keyword was not found.
