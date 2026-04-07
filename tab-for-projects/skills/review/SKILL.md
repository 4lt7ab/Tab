---
name: review
description: "Retrospective — did we build what we planned? Is the KB accurate? Use when the user wants to review progress, check quality, or run a retrospective, or invokes /review."
argument-hint: "<project ID or title>"
---

# Review — Retrospective

The look-back play. Dispatches the Project Manager and Tech Lead in parallel — PM checks progress against the plan, Tech Lead audits KB accuracy — then synthesizes both into a retrospective. Use this after a batch of work lands, or when you want an honest assessment of where things stand versus where they should be.

## Trigger

**When to activate:**
- The user runs `/review`
- The user asks "did we build what we planned?" or "how did that go?"

**When NOT to activate:**
- The user wants current status (that's `/status` — forward-looking, not retrospective)
- The user wants to fix problems (that's `/maintain`)
- The user wants to plan new work (that's `/plan`)

## Arguments

- If a project ID or title is provided, resolve it.
- If omitted, list projects via `list_projects` and ask the user which one.
- If only one project exists, use it without asking.

## Sequence

1. **Dispatch Project Manager and Tech Lead in parallel.** These two dispatches are independent — neither needs the other's output.

   **Project Manager** with:
   - `project_id`: the resolved project ID
   - `focus`: `progress`

   The PM assesses: what's done vs. planned, status accuracy, stale work, dependency health, whether completed tasks match what was actually built.

   **Tech Lead** with:
   - `project_id`: the resolved project ID
   - `dispatch_type`: `audit`

   The TL assesses: does the KB reflect current reality? Are docs stale, redundant, or missing? Do documented patterns still match the codebase?

2. **Read both reports.** Extract from the PM report:
   - Done-to-total ratio and trajectory
   - Gaps between plan and execution (tasks that deviated, scope that expanded)
   - Status accuracy (are done tasks really done? are in-progress tasks really active?)
   - Dependency health post-completion

   Extract from the TL report:
   - KB accuracy (docs that are stale or drifted)
   - Coverage gaps (things that should be documented but aren't)
   - Redundancies (docs that overlap and should be merged)
   - KB health assessment

3. **Synthesize into a retrospective.**

## Output

Present the retrospective:

**Progress** — What was accomplished. Done-to-total ratio, key completions, trajectory. Is the project ahead, on track, or behind where it should be?

**Plan vs. reality** — Where execution deviated from the plan. Tasks that grew in scope, approaches that changed, work that was discovered mid-build. This isn't a judgment — deviations are normal. The value is making them visible.

**KB health** — Is the documentation keeping up with the code? Stale docs, gaps, redundancies. Specific recommendations if the TL flagged issues.

**What's next** — Based on both reports, what should happen now? Concrete recommendations: tasks to prioritize, docs to update, decisions to make. One or two actionable next steps, not a laundry list.

## Edge Cases

- **No completed tasks:** The retrospective is about what hasn't happened yet — blockers, readiness, whether the plan is set up for success. Still valuable.
- **Everything is done:** The project may be ready to close. Recommend a final KB curation pass and note any follow-up work discovered during implementation.
- **PM and TL disagree:** Surface both perspectives. If the PM says tasks are done but the TL says docs are stale, that's a real finding — the code moved but the knowledge didn't keep up.
