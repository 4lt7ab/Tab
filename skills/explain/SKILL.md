---
name: explain
description: "Use when the user wants something explained — says things like 'explain this', 'explain X to Y', 'help me understand', 'break this down', 'ELI5', 'what does this mean'. Not for teaching a course — for landing a concept with a specific audience."
argument-hint: "[topic, optionally 'to [audience]']"
---

## What This Skill Does

Research-backed, audience-aware explanations. Picks the right depth, format, and vocabulary for who's listening. Knows that an expert needs one sentence where a newcomer needs five paragraphs — and delivers accordingly.

Always inline. No file output.

## How It Works

1. **Identify the audience.** Explicit ("explain to my PM") or inferred from context. If the level is clear, don't ask. If it's ambiguous, ask.
2. **Research the topic.** Don't just explain from what you know. Search for good analogies, existing explanations, tutorials, prior art. Understand the best way this has been taught before and build from that.
3. **Choose the format.** The shape of the explanation follows the audience, not a fixed template:
   - **Executive / non-technical** — bullet summary, lead with "why it matters," no jargon. Break down to business impact, not technical mechanism.
   - **New to the domain** — narrative walkthrough, build one concept at a time, concrete examples. Every new idea gets its own moment.
   - **Technical peer** — annotated walkthrough, skip basics, focus on how and why. Decompose at the system level, not the concept level.
   - **Expert** — precise, dense, focus on nuance and tradeoffs. Don't decompose what they already know — go straight to the interesting part.
4. **Deliver.** Conversational. The explanation lives in the conversation — not in a file.

## Principles

- **Research before explaining.** Find how something's been taught well before improvising. Good analogies exist — find them.
- **Decompose to the audience's level.** The right explanation isn't simpler words — it's the right *granularity*. Over-decomposing for experts is patronizing; under-decomposing for newcomers leaves them lost.
- **Examples at every level.** Examples aren't just for beginners — they're how ideas land. Use concrete ones.
- **Cut ruthlessly.** If a detail doesn't serve the audience's understanding at their level, it's noise.

## Execution

Scales with complexity. Quick, single-concept explanations run inline immediately. Research-heavy explanations run as a subagent via the Agent tool, then deliver the result conversationally.
