---
name: maintain
description: "Housekeeping sweep — clean up task shape, curate the KB, freshen CLAUDE.md files. Use when the project needs cleanup, grooming, or curation, or invokes /maintain."
argument-hint: "<project ID or title>"
---

# Maintain — Housekeeping Sweep

The sharpen-the-tools play. Dispatches the Project Manager and Tech Lead in parallel to clean their respective domains, then conditionally dispatches the Developer if in-code documentation needs attention. Use this when things feel messy — stale tasks, bloated KB, drifted docs — or on a regular cadence to keep the project tight.

## Trigger

**When to activate:**
- The user runs `/maintain`
- The user asks to "clean up" or "tidy" a project

**When NOT to activate:**
- The user wants a status check (that's `/status` — read-only, lighter weight)
- The user wants a retrospective (that's `/review` — backward-looking analysis)
- The user wants to build features (that's `/build`)

## Arguments

- If a project ID or title is provided, resolve it.
- If omitted, list projects via `list_projects` and ask the user which one.
- If only one project exists, use it without asking.

## Sequence

1. **Dispatch Project Manager and Tech Lead in parallel.** These two operate on independent domains — task shape and KB documents — so they can run simultaneously.

   **Project Manager** with:
   - `project_id`: the resolved project ID
   - `focus`: omitted (full health check)

   The PM runs its full diagnostic and fixes what it owns: missing descriptions, stale statuses, broken dependencies, ungrouped tasks, miscalibrated effort.

   **Tech Lead** with:
   - `project_id`: the resolved project ID
   - `dispatch_type`: `curate`

   The TL runs its health protocol: merges overlapping docs, prunes stale ones, fixes tagging inconsistencies, enforces count discipline.

2. **Read both reports.**

   From the PM report, extract:
   - What was fixed (task shape corrections, dependency rewiring, status resets)
   - Remaining issues that need human decisions
   - Any flags about CLAUDE.md gaps (the PM may note areas where in-code docs are missing or stale based on task context)

   From the TL report, extract:
   - Documents merged, updated, or deleted
   - KB health assessment (count, coverage, accuracy)
   - Gaps identified

3. **Conditionally dispatch Developer.** Only if the PM report flags stale or missing CLAUDE.md files.

   **Developer** in analysis mode with:
   - `scope`: the specific directories or modules where CLAUDE.md files need attention (extracted from the PM report)
   - `project_id`: the resolved project ID

   The Developer checks CLAUDE.md coverage and accuracy for the flagged areas and updates them as needed.

   **If the PM did not flag CLAUDE.md issues, skip this step entirely.**

4. **Read the Developer's report** (if dispatched). Extract:
   - CLAUDE.md files created or updated
   - Areas checked and found accurate (no changes needed)

## Output

Present the maintenance summary:

**Task health** — What the PM fixed. Task shape corrections, dependency rewiring, status resets, grouping changes. If nothing needed fixing, say the tasks are healthy.

**KB health** — What the TL curated. Documents merged, pruned, retagged. Current doc count and assessment. If nothing needed curation, say the KB is clean.

**In-code docs** — What the Developer updated (if dispatched). CLAUDE.md files created or refreshed. If the Developer was not dispatched, note that in-code docs were not flagged as needing attention.

**Still needs attention** — Anything that requires human decisions, other agent work, or follow-up. Omit if everything was handled.

## Edge Cases

- **Nothing needs fixing anywhere:** Great — report a clean bill of health across all three domains. A maintenance run that finds nothing wrong is a success, not a waste.
- **PM and TL reports conflict:** Possible if the PM flags a KB gap that the TL just pruned. Surface both findings and let the user decide.
- **Developer finds extensive CLAUDE.md drift:** The Developer may report that many files need updating. If the scope is large, it reports what it found and what it fixed — but the maintenance play is about a sweep, not a deep rewrite. Flag anything beyond a sweep for a dedicated `/investigate` run.
