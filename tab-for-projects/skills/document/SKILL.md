---
name: document
description: "Capture knowledge from completed work — extract decisions, patterns, and gotchas from the codebase and write them into MCP knowledgebase documents."
argument-hint: "[project-name] [task-ids or focus area]"
---

# Document

Extract knowledge from completed work and write it into the project's knowledgebase. The goal is internal knowledge artifacts for future agents — planners, QA, coordinators, implementers. Not READMEs. Not user-facing docs.

## Protocol

### 1. Load Context

1. Resolve the project. If the user passed an argument, match it against `list_projects`. Otherwise follow standard resolution.
2. Call `get_project` for goal, requirements, and design.
3. Call `get_task` for each task ID to pull the full record — title, description, plan, implementation, acceptance criteria. The `plan` and `implementation` fields are the richest source of what was intended vs. what actually happened.
4. Call `list_documents` with the project ID to see what knowledge already exists. Scan titles and tags to understand the current knowledgebase landscape.
5. If documents overlap with what you're about to write, call `get_document` to read them before writing.

### 2. Research the Codebase

Task records tell you what was planned — the code tells you what actually happened.

- **Read the files that were changed.** The task's `implementation` field usually references specific files. Read the actual code, not just the summary.
- **Look for patterns.** Naming, module structure, conventions followed or established by this work.
- **Look for decisions.** When the implementation diverged from the plan, why? When multiple approaches were possible, what was chosen and what was the trade-off?
- **Look for gotchas.** What's non-obvious? What would trip up someone working in this area for the first time?
- **Read surrounding code.** Don't just read changed files — read what they integrate with. Integration seams are where the most useful knowledge lives.

Use `Glob`, `Grep`, `Read`, and `Bash` tools freely. The value of what you write is proportional to how well you understood the code.

### 3. Check Before You Write

- **If a document already covers this topic**, call `update_document` rather than creating a duplicate. Add new sections, refine existing ones, note how the latest work changed or confirmed previous understanding.
- **If the topic is new**, call `create_document` (accepts `title`, `content`, `tags` only). Then **immediately attach it** by calling `update_project` with `attach_documents` containing the new document's ID. Without this step, the document is invisible to future agents.

The knowledgebase should grow in depth, not just breadth. Ten well-maintained documents beat fifty stale ones.

### 4. Write the Knowledge

Each document should be focused on a single topic or theme. Extract distinct knowledge threads and give each its own document (or merge into an existing one).

## What to Capture

| Category | What to write | Example |
|----------|--------------|---------|
| **Architecture decisions** | What was decided, alternatives, why this was chosen | "Chose event-driven over polling for sync because..." |
| **Patterns established** | Naming, file structure, integration patterns, code organization | "All MCP tool handlers follow: validate, fetch, transform, respond" |
| **Gotchas** | Non-obvious constraints, edge cases, things that broke | "MCP returns dates as ISO strings without timezone — treat as UTC" |
| **Design trade-offs** | What was traded for what, when to revisit | "Chose simplicity over flexibility — if we need more than 3 types, refactor to a registry" |
| **Integration points** | How components connect, contracts, where the seams are | "The planner depends on task.description being non-empty" |

## Document Type Templates

### Pattern Record

```markdown
## Pattern: [name]

**Established in:** [task title or ID]
**Applies to:** [where this pattern should be followed]

[2-3 sentence summary]

### How it works

[Concrete description with file paths and code references]

### Why this approach

[Rationale — what was considered, what was chosen, why]

### Watch out for

[Gotchas, edge cases, constraints]
```

### Decision Record

```markdown
## Decision: [what was decided]

**Context:** [what prompted the decision]
**Decided:** [the choice made]
**Alternatives considered:** [what else was on the table]
**Trade-offs:** [what was gained, what was given up]
**Revisit when:** [conditions that would change this decision]
```

### Reference Document

```markdown
## [Topic] Reference

[Concise description of what this covers]

### [Section]

[Concrete details — file paths, config shapes, API contracts, lookup tables]
```

### Troubleshooting Guide

```markdown
## Troubleshooting: [area]

### [Symptom]

**Cause:** [what's actually happening]
**Fix:** [what to do]
**Prevention:** [how to avoid this in the future]
```

Not every document needs a template. Use what fits. The goal is precision and usefulness, not template compliance.

## Tagging

Every document must have tags. This is a **closed enum** — only these values are valid:

`ui`, `data`, `integration`, `infra`, `domain`, `architecture`, `conventions`, `guide`, `reference`, `decision`, `troubleshooting`, `security`, `performance`, `testing`, `accessibility`

Common usage:

- `architecture` — structural decisions, component relationships
- `conventions` — established conventions, naming, file structure, code style norms
- `decision` — specific decision records with rationale
- `troubleshooting` — non-obvious traps, edge cases, gotchas
- `integration` — how components connect and depend on each other
- `reference` — API contracts, config shapes, lookup tables

Use 1-3 tags per document. Pick the most relevant, not all that could apply.

## Completion

Report back:

- How many documents created vs. updated
- Brief list of what was documented (one line per document — title and why it matters)
- Any knowledge gaps noticed but not filled (e.g., "the task didn't record why polling was rejected")
