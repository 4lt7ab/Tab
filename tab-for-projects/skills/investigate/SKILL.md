---
name: investigate
description: "Understand how something works in the codebase and persist that understanding as knowledge."
argument-hint: "<what to investigate — module, subsystem, pattern, or question>"
mode: headless
agents:
  - tab-for-projects:developer
  - tab-for-projects:tech-lead
requires-mcp:
  - tab-for-projects
---

# Investigate — Code Understanding to KB

The knowledge-building play. Dispatches the Developer to analyze code, then the Tech Lead to persist findings as KB documentation. Turns understanding into durable, reusable knowledge. Use this when you need to understand how something works and want that understanding to survive the session.

## Trigger

**When to activate:**
- The user runs `/investigate`
- The user asks "how does X work and document it" or wants codebase understanding captured in the KB

**When NOT to activate:**
- The user just wants a quick answer about how something works (that's a normal conversation, not a skill)
- The user wants code changed (that's `/build`)
- The user wants to check project health (that's `/status`)

## Arguments

- The argument is the investigation scope — a module, subsystem, directory, file, pattern, or question.
- A project ID or title may optionally be included for KB context. If omitted and only one project exists, use it. If multiple projects exist, ask which one the findings should be documented under.

## Sequence

1. **Dispatch Developer** in analysis mode with:
   - `scope`: the investigation target from the user's argument
   - `project_id`: the resolved project ID (if available)
   - `document_ids`: IDs of relevant KB documents (search the KB first for existing docs on the topic)

   The Developer reads the code, understands patterns and architecture, checks CLAUDE.md coverage, and returns an analysis report.

2. **Read the Developer's analysis report.** Extract:
   - Summary (what was found)
   - Findings (specific observations with file references)
   - CLAUDE.md status (does the area have in-code docs? are they accurate?)
   - Conventions observed (patterns that may warrant KB documentation)

3. **Search existing KB documents** for the topic to determine whether to create or update:
   ```
   list_documents({ search: "<topic>" })
   ```
   - If a relevant document exists, the Tech Lead should update it.
   - If the topic is genuinely new to the KB, the Tech Lead should create a new document.

4. **Dispatch Tech Lead** with:
   - `project_id`: the resolved project ID
   - `dispatch_type`: `update` if existing doc found, `write` if new topic
   - `scope`: the topic area investigated
   - `context`: the Developer's full analysis report — findings, file references, conventions, CLAUDE.md status

   The Tech Lead writes or updates KB documentation grounded in the Developer's concrete findings.

5. **Read the Tech Lead's KB report.** Extract:
   - Documents created or updated (IDs and titles)
   - KB health assessment

## Output

Present the findings to the user:

**What was learned** — Summary of the Developer's analysis. Key findings, architecture observations, patterns discovered. Keep it concise but reference specific files.

**What was documented** — KB documents created or updated, with titles. Note whether this was a new document or an update to an existing one.

**CLAUDE.md status** — Whether the investigated area has in-code documentation and whether it's accurate. If gaps were found, note them.

**Conventions discovered** — Any patterns observed that are now captured in the KB for future reference.

## Edge Cases

- **No project context:** The Developer can still analyze code without a project ID. But the Tech Lead needs a project to attach documents to. If no project exists, tell the user the findings are available but can't be persisted to the KB without a project. Suggest `/kickoff`.
- **Investigation finds nothing notable:** Report that. A clean bill of health is a finding. The Tech Lead may not need to create or update anything — that's fine.
- **KB is at capacity (13 docs):** The Tech Lead handles this via its own count discipline — it will merge or prune before creating. Tab does not need to intervene.
