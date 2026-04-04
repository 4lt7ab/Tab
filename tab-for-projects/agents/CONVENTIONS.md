# Agent Conventions

Three structural rules at the seams. The workflow in the middle is fully agent-specific.

## 1. Opening Paragraph

Three sentences, always in this order:

1. **Role** — what this agent is and what it produces.
2. **Invocation** — how it's triggered and what it receives.
3. **Constraint** — the single most important boundary (who it talks to, what it doesn't do).

This is the highest-weight position in the prompt. Standardizing it costs nothing per agent and buys reliable orientation.

## 2. Shared Vocabulary

Cross-cutting operations use canonical names. Agent-specific operations use agent-specific names.

| Canonical term | Meaning | Used by |
|---|---|---|
| **Load Context** | The MCP-reading phase — pull project, task, and document data before doing work. Every agent's first workflow step. | All agents |
| **Return** | The final output sent back to the caller. What the caller gets and what it contains. | Headless agents |

Everything else — codebase research, verification, writing knowledge, pair programming — is agent-specific and named for what the agent actually does. The planner's "Research the Codebase" is exploration. QA's "Inspect the Actual Work" is verification. The documenter's "Research the Codebase" is extraction. These are different operations that happen to involve reading code. Don't flatten them.

## 3. Boundaries

Every agent closes with explicit boundaries: what it does NOT do and how it hands off. For headless agents, this is a `## Boundaries` section. For conversational agents, the boundaries are woven into the agent's structure where they carry the most weight (e.g., the manager's hard rule at the top).

Boundaries are short, declarative, and unnegotiated. They answer: if the agent is tempted to do X, should it? The answer is always no — hand it off.

## 4. MCP Data Model

You manage three layers of the Tab for Projects MCP: **projects**, **tasks**, and **documents**.

### Projects

The top-level container. A project has a **title**, **goal**, **requirements**, and **design**. These fields are the strategic memory — they capture *why* work is happening, not just *what* work exists.

When the user talks about what they're building, why they're building it, or how it should work, that's project-level information. Update the right field. Don't let good context evaporate into chat history.

### Tasks

The unit of trackable work. Tasks live inside a project and have rich fields:

| Field | What it's for |
|-------|--------------|
| **title** | Short, scannable, action-oriented |
| **description** | The memory — write for someone reading next week with no context |
| **plan** | How to approach the work, phasing, sequencing |
| **implementation** | What was actually done (filled after the fact, not before) |
| **acceptance_criteria** | What "done" looks like — only if the user has stated this |
| **effort** | trivial / low / medium / high / extreme |
| **impact** | trivial / low / medium / high / extreme |
| **category** | feature / bugfix / refactor / test / perf / infra / docs / security / design / chore |
| **group_key** | Flat grouping label (max 32 chars) for organizing related tasks |
| **status** | todo / in_progress / done / archived |

### Documents

The knowledgebase layer. Documents are **independent top-level entities** — they aren't owned by any single project. A document has a **title**, optional **content** (markdown, up to 100k chars), and optional **tags** for organization. Documents can be linked to one or more projects via a many-to-many relationship.

**Creating and linking:**
- `create_document` creates a standalone document (accepts `title`, `content`, `tags` only — no project ID).
- To link a document to a project, call `update_project` with `attach_documents: [doc_id, ...]`.
- To unlink, call `update_project` with `detach_documents: [doc_id, ...]`.

**Browsing:** `list_documents` returns lightweight summaries (id, title, has_content, tags, timestamps) and supports filtering by tag, title, or `project_id` (which filters through the link table to return docs linked to that project). `get_project` also returns linked document summaries in its `documents` array.

Use `update_document` to modify documents directly. When updating, only provided fields change; providing tags replaces all existing tags.

**Avoid calling `get_document` in the main thread by default.** Document content can be massive — pulling it into the conversation wastes context on content the user may not need to see verbatim. When passing documents to subagents, pass the IDs only and let the subagent fetch the content itself. **But if the user explicitly asks to see a document's content, call `get_document` directly** — don't make them wait for a subagent just to read their own doc.

**Batch and filter.** All create/update tools accept `items` arrays — use batch calls when creating or updating multiple tasks at once. When listing tasks, use the available filters (`status`, `effort`, `impact`, `category`, `group_key`) to pull exactly what's needed instead of fetching everything.

**Default to active work.** When listing tasks, only show `todo` and `in_progress` by default. Done and archived tasks are history — don't surface them unless the user explicitly asks.

When showing tasks, keep it scannable — title, status, and enough context to know what it's about. Drill into details when the user wants them.

## 5. List vs. Get

All three layers follow the same pattern: **list** returns lightweight summaries (id, title, status, timestamps, and a few key fields), **get** returns the full record with all fields. Use list for scanning and filtering; use get when you need the details. Don't call get on every item — only drill in when the user wants depth.

**Exception: `get_document`.** Documents can contain up to 100k characters of markdown. You call `list_documents` directly (it's lightweight), but you should **avoid calling `get_document` in the main thread by default** — when subagents need document content for their work, pass the IDs and let them fetch it. The exception is when the user explicitly asks to see a document — then call `get_document` directly so they're not waiting on a subagent for a simple read.

## 6. Knowledgebase Context for Subagents

Before spawning, check if the project has relevant documents by calling `list_documents`. If you see architecture docs, conventions, or design decisions that would help the agent's work, include the document IDs in its prompt so it can fetch and use them. Don't fetch the content yourself — just pass the IDs.
