---
name: document
description: "Extract knowledge from completed work — research the codebase, check existing docs, and write focused knowledgebase documents with proper tagging and project attachment."
argument-hint: "[project-id task-ids...]"
inputs: "project-id (required), task-ids[] (required — completed tasks to document), focus (optional — e.g. 'capture the auth pattern'), knowledgebase-doc-ids[] (optional — existing docs to check/update)"
mode: headless
agents:
  - documenter
requires-mcp: tab-for-projects
---

# Document

## Research the Codebase

This is where the real knowledge lives. Task records tell you what was planned — the code tells you what actually happened.

- **Read the files that were changed.** The task's `implementation` field usually references specific files. Go read them. Look at the actual code, not just the summary.
- **Look for patterns.** How are things named? How are modules structured? What conventions were followed (or established) by this work?
- **Look for decisions.** When the implementation diverged from the plan, why? When multiple approaches were possible, what was chosen and what was the trade-off?
- **Look for gotchas.** What's non-obvious? What would trip up someone working in this area for the first time? What constraints aren't visible from the outside?
- **Look at surrounding code.** Don't just read the changed files — read what they integrate with. The integration seams are where the most useful knowledge lives.

Use `Glob`, `Grep`, `Read`, and `Bash` tools freely. Be thorough. The value of what you write is directly proportional to how well you understood the code.

## Check Before You Write

Before creating any document, check the existing knowledgebase:

- **If a document already covers this topic**, update it with `mcp__tab-for-projects__update_document` rather than creating a duplicate. Add new sections, refine existing ones, note how the latest work changed or confirmed previous understanding. No re-linking needed — existing documents are already attached to the project.
- **If the topic is new**, create a new document with `mcp__tab-for-projects__create_document` (accepts `title`, `content`, `tags` only — no `project_id`). Then **immediately attach it to the project** by calling `mcp__tab-for-projects__update_project` with `attach_documents` containing the new document's ID. Without this step, the document is an orphan — invisible to future agents querying the project's knowledgebase.

The knowledgebase should grow in depth, not just in breadth. Ten well-maintained documents beat fifty stale ones.

## Write the Knowledge

Each document should be focused on a single topic or theme. Don't create one mega-document per task — extract the distinct knowledge threads and give each its own document (or merge into an existing one).

### What to Capture

| Category | What to write | Example |
|----------|--------------|---------|
| **Architecture decisions** | What was decided, what alternatives existed, why this was chosen | "Chose event-driven over polling for sync because..." |
| **Patterns established** | Naming conventions, file structure, integration patterns, code organization | "All MCP tool handlers follow the pattern: validate → fetch → transform → respond" |
| **Gotchas** | Non-obvious constraints, edge cases, things that broke during implementation | "The MCP API returns dates as ISO strings but without timezone — always treat as UTC" |
| **Design trade-offs** | What was traded for what, and under what conditions the trade-off should be revisited | "Chose simplicity over flexibility here — if we need more than 3 document types, refactor to a registry" |
| **Integration points** | How components connect, what contracts they depend on, where the seams are | "The planner agent depends on task.description being non-empty — empty descriptions produce garbage plans" |

### Document Structure

Write markdown. Be concrete. Reference file paths. Include code snippets when they illustrate a pattern. Structure for scanability — headers, bullet points, short paragraphs.

A good document looks like:

```markdown
## Pattern: [name]

**Established in:** [task title or ID]
**Applies to:** [where this pattern should be followed]

[2-3 sentence summary of the pattern]

### How it works

[Concrete description with file paths and code references]

### Why this approach

[Rationale — what was considered, what was chosen, why]

### Watch out for

[Gotchas, edge cases, constraints]
```

Not every document needs every section. Use what fits. The goal is precision and usefulness, not template compliance.

### Tags

Every document must have tags. This is a **CLOSED enum** — only these values are valid (not extensible):

`ui`, `data`, `integration`, `infra`, `domain`, `architecture`, `conventions`, `guide`, `reference`, `decision`, `troubleshooting`, `security`, `performance`, `testing`, `accessibility`

Common usage:

- `architecture` — structural decisions, component relationships
- `conventions` — established conventions, naming, file structure, code style norms
- `decision` — specific decision records with rationale
- `troubleshooting` — non-obvious traps, edge cases, gotchas
- `integration` — how components connect and depend on each other
- `reference` — API contracts, config shapes, lookup tables

Use 1-3 tags per document. Pick the most relevant, not all that could apply.
