---
name: feedback
description: "Use when the user runs /feedback or explicitly asks for structured, graded feedback on an artifact, idea, or approach."
argument-hint: "[artifact, idea, or approach to evaluate]"
---

## What This Skill Does

Structured, research-backed feedback. Works on existing artifacts (code, docs, plans) and ideas in context ("I'm thinking about doing X"). Inline execution, no file output.

## How It Works

1. **Understand the full scope.** Read everything relevant before reacting. If it's code, read the whole file (and imports/dependents if needed). If it's a plan, understand the goal and constraints. If it's an idea, ask enough to evaluate it — but don't over-interrogate. Get the big picture.
2. **Form the overall take.** Commit to a one-sentence verdict before writing any detail. The verdict sets the frame — everything after it supports or explains it.
3. **Research where needed.** If the artifact involves a domain, pattern, or technology where best practices matter, search for them — web search, codebase scan, documentation. Ground feedback in evidence, not intuition. Skip this for things where opinion is the point.
4. **Filter.** Before writing a single finding, ask: would I act on this if I received it? If not, cut it. Fewer sharp findings beat a long list of marginal ones.
5. **Grade it.** Assign a letter grade (A–F) that captures the overall quality. The grade is a signal — A/B means solid, C means notable issues, D/F means fundamental problems. Commit to the grade before writing findings.
6. **Deliver.** Lead with the grade and verdict. Then feedback ordered by importance, most critical first. Each point: what's wrong (or right), why it matters, and what you'd do instead.

## Principles

- **Productivity over thoroughness.** If feedback isn't important enough to act on, don't mention it.
- **Ideas, not just artifacts.** "I'm thinking about doing X" gets evaluated on its merits — tradeoffs, risks, whether it's been tried before, what usually goes wrong.
- **Challenge the approach, not just the execution.** Sometimes the problem isn't how something was done but that it was done at all.
- **Distinguish taste from truth.** Signal which feedback is objective ("this will break when X") vs. opinion ("I'd structure this differently"). Both are valid; conflating them isn't.
- **If it's good, say so and stop.** Name what's worth stealing. Don't manufacture criticism to seem thorough.
- **Match depth to the artifact.** Code gets design-level feedback, not lint. Prose gets clarity and structure, not grammar. Plans get feasibility and gap analysis, not formatting.
- **Read tool wins over session context.** When evaluating code or docs, trust what the Read tool returns over anything in session context. If they conflict, name the conflict and trust the file.
