---
name: curate
description: "Knowledgebase curation — find duplicates, check staleness, verify tags and references, consolidate overlapping documents, and retire outdated ones."
argument-hint: "[project-name]"
---

# Curate

Review the project's knowledgebase for health and coherence. The goal is a knowledgebase that grows in depth, not just breadth — ten well-maintained documents beat fifty stale ones.

## Protocol

### 1. Load Context

1. Resolve the project. If the user passed an argument, match it against `list_projects`. Otherwise follow standard resolution.
2. Call `get_project` for goal, requirements, and design.
3. Call `list_documents` for the project. Pull the full list — titles, tags, and IDs.
4. Call `get_document` for each document to read full content.

### 2. Curation Checklist

Walk through every document and assess:

**Duplicates.** Do any documents cover the same topic? Look for overlapping titles, similar tags, and content that restates the same knowledge. Flag pairs or clusters.

**Staleness.** Does the document describe something that has since changed? Cross-reference against the codebase — if file paths, patterns, or conventions mentioned in the document no longer exist or have been superseded, the document is stale.

**Tag accuracy.** Are tags from the closed enum (`ui`, `data`, `integration`, `infra`, `domain`, `architecture`, `conventions`, `guide`, `reference`, `decision`, `troubleshooting`, `security`, `performance`, `testing`, `accessibility`)? Are they accurate for the content? Are there 1-3 tags per document?

**Reference integrity.** Do documents reference task IDs, file paths, or other documents that still exist? Broken references erode trust in the knowledgebase.

**Favorites.** Which documents are genuinely useful — the ones that would save a future agent 10 minutes of exploration or prevent a mistake? Mark these as high-value.

### 3. Consolidation

For duplicate clusters, merge into a single document:

1. Pick the best document as the base (most complete, best structured).
2. Pull unique content from the others into the base using `update_document`.
3. Delete the redundant documents using `delete_document`.

For documents that partially overlap but cover distinct angles, restructure:

1. Extract the shared content into one document.
2. Refocus each remaining document on its unique contribution.
3. Update tags to reflect the new scope.

### 4. Retirement

Remove documents that meet any of these criteria:

- **Fully superseded.** Another document covers the same ground with more current information.
- **Describes deleted code.** The files, patterns, or systems it documents no longer exist in the codebase.
- **Empty or placeholder.** No substantive content.

Before deleting, check whether any useful fragment should be preserved — fold it into a surviving document first, then delete.

Use `delete_document` for removal. There is no archive — retirement means deletion.

### 5. Fixes

For documents that survive curation but need updates:

- **Stale content** — update with current state from the codebase.
- **Wrong tags** — fix to match content using the closed enum.
- **Broken references** — update or remove dead links and IDs.
- **Missing tags** — add 1-3 accurate tags.

Use `update_document` for all fixes.

## Completion

Report back:

- Total documents reviewed
- Documents consolidated (merged into fewer)
- Documents retired (deleted, with reasons)
- Documents updated (tag fixes, stale content refreshed, broken references repaired)
- High-value documents identified (title and why they matter)
- Remaining gaps — topics the knowledgebase should cover but doesn't
