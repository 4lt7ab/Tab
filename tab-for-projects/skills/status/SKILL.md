---
name: status
description: "Quick project health brief — what's ready, blocked, stale, and progressing."
argument-hint: "<project ID or title>"
mode: headless
agents:
  - project-manager
requires-mcp:
  - tab-for-projects
---

# Status — Project Health Brief

The lightest play in the playbook. Dispatches the Project Manager for a full health check and synthesizes the report into a concise brief. No writes, no fixes beyond what the PM autonomously handles in its own domain. Use this to get bearings on a project — what's moving, what's stuck, what needs attention.

## Trigger

**When to activate:**
- The user runs `/status`
- The user asks "what's the status of my project?" or "where do things stand?"

**When NOT to activate:**
- The user is asking about a specific task (that's a task lookup, not a health brief)
- The user wants to fix problems (that's `/maintain`)
- The user wants a retrospective on completed work (that's `/review`)

## Arguments

- If a project ID or title is provided, resolve it to a project.
- If omitted, list projects via `list_projects` and ask the user which one.
- If only one project exists, use it without asking.

## Sequence

1. **Dispatch Project Manager** with:
   - `project_id`: the resolved project ID
   - `focus`: omitted (full health check)

   The PM runs its full diagnostic — project fields, task shape, dependencies, progress — and fixes what it owns autonomously (missing descriptions, stale statuses, broken dependencies).

2. **Read the PM health report.** Extract:
   - Health summary (one sentence)
   - What was fixed (task shape corrections, dependency rewiring)
   - Ready tasks (unblocked, well-formed, waiting for a developer)
   - Blocked tasks and why
   - Stale or stuck work
   - Needs tech lead (KB gaps, tasks needing codebase investigation)
   - Needs human decision (ambiguous requirements, scope questions)
   - Progress assessment (is the project moving?)

3. **Synthesize into a brief for the user.** Do not dump the raw PM report. Distill it.

## Output

Present the brief in this structure:

**Progress** — One sentence. Is the project moving? What's the trajectory?

**Ready to build** — Tasks that are unblocked and well-formed, with IDs and titles. If nothing is ready, say so and explain why.

**Blocked** — Tasks waiting on something, with what's blocking them. Omit if nothing is blocked.

**Fixed** — What the PM cleaned up during the health check. Omit if nothing was fixed.

**Needs attention** — Things that require human decisions or other agents. KB gaps that need the tech lead, ambiguous requirements that need the user. Omit if nothing needs attention.

Omit empty sections entirely. A healthy project with no blockers should produce a short, clean brief.

## Edge Cases

- **No projects exist:** Tell the user there are no projects yet and suggest `/kickoff` to start one.
- **Project has no tasks:** Report the project fields health (goal, requirements, design) and note that no tasks exist yet. Suggest `/plan` to decompose work.
- **Everything is done:** Celebrate briefly. Note the project may be ready to close or that `/review` can provide a retrospective.
- **PM reports nothing to fix:** That's good — it means the project is healthy. The brief should reflect that clearly.
