---
name: workshop
description: "Collaborative planning for non-trivial decisions. Use when the user is exploring how to approach something, weighing alternatives, or expressing uncertainty about direction — even if they don't use words like 'workshop' or 'plan'. If the user seems to be thinking through a problem rather than asking for a specific action, invoke this skill. Do not answer exploratory design questions directly — use this skill to structure the thinking. Also triggers on /workshop."
argument-hint: "[idea or problem to workshop]"
---

A continuous planning session that shapes a raw idea into an in-depth implementation plan. The conversation drives the process — not a rigid set of steps. Actively researches (web search, codebase exploration) to ground the discussion in reality, and maintains a living document that evolves as the plan takes shape.

## Opening

1. Read the idea. Restate it back in one or two sentences to confirm understanding. **Stop and wait for confirmation before doing anything else.**
2. Once confirmed, do initial research — scan relevant files in the project and run a few web searches to understand the landscape. Share what you find.
3. Write a **rough sketch** to `docs/plans/<topic>.md`, where `<topic>` is a short kebab-case name derived from the idea (e.g., `docs/plans/auth-rewrite.md`). Mention the path so the user knows where it lives. This is the seed. It will be wrong and incomplete. That's the point.

## Plan Template

The plan file follows this structure. Sections gain resolution over time — they grow, shrink, merge, or get cut as the thinking evolves.

```markdown
# <Plan Title>

## Goal
What we're trying to accomplish and why.

## Approach
The current thinking on how to get there.

## Decisions
Choices that have been made and the reasoning behind them.

## Open Questions
Things that still need to be figured out before this plan is ready.
- [ ] ...
```

## The Loop

Each pass through the loop:

- **React to what the user said.** They might challenge an assumption, ask to zoom into a section, redirect entirely, or confirm something is solid. Follow their direction, but push back on reasoning that doesn't hold up.
- **Research before proposing.** Do not propose an approach without first checking whether an existing solution already handles it. If a question comes up that you can't answer confidently, search for it — existing solutions, libraries, patterns, prior art, project files for constraints and conventions. Share findings conversationally — synthesize, don't dump links. "Looks like X library handles this, but Y might be a better fit because..."
- **Pressure-test the approach.** Surface assumptions the user hasn't stated, trade-offs they haven't weighed, failure modes they haven't considered. Don't just research *for* the plan — research *against* it. If there's a reason this won't work, find it now.
- **Update the plan file.** When the conversation *lands* — a decision is made, an open question gets resolved, the approach shifts — update the file. Don't update during exploratory back-and-forth that hasn't settled yet. If you're not sure whether something has landed, it probably hasn't.
- **Name it when it stalls.** If the conversation isn't converging after several passes, say so. Name the block and ask whether to narrow scope or pivot.
- **Name it when it sprawls.** If the scope is growing beyond what one session can resolve, say so. Suggest breaking into focused sessions rather than producing a plan too broad to implement from.

## Closing

The workshop is done when **Open Questions is empty** — every item has been resolved, answered, or consciously deferred to implementation.

When that happens, say so clearly: the plan is ready, the workshop is complete. Let the user know they can reopen the plan and add new questions any time to kick off another session.
