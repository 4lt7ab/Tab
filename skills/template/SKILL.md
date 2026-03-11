---
name: template
description: "Use when the user wants to define a reusable template for a recurring type of work — says things like 'template this', 'let's make a template for', 'help me define a template for', 'create a template for X type of work'."
argument-hint: "[type of work to template]"
---

## What This Skill Does

A guided session that produces a precise, reusable reference doc for a recurring type of work. The output is a standing specification — not a dated artifact, but a living document the user hands to workshop or draft as context when starting a new session of this type.

Fills the gap between skills: workshop shapes thinking, draft generates steps, and template encodes *a type of thing* so both can be done with precision and consistency every time.

## Output Directory

Tab writes to `<output-dir>/<topic>/template-<pattern>.md`. Tab always asks for the topic before writing and creates the directory if needed.

## How It Works

The session runs in two phases: discovery, then interview.

### Phase 1 — Discovery

Before asking the user anything, research prior art. Find existing examples of this type of work — in the codebase, docs, files, or whatever's in scope — read conventions, identify constraints, map relevant locations. The goal: arrive at the interview already knowing everything that can be inferred, so the interview only covers what *can't* be. If there's no prior art to find, say so upfront and move directly to the interview.

Name what you found and what you couldn't infer before asking the first question. "I found three existing examples of X — they all use Y convention. What I couldn't infer is..."

**Readiness check.** Before proceeding, assess whether this type of work is settled enough to template. Signals it isn't: no existing examples, inconsistent patterns across examples, or the definition of the work type itself is still open. If any of these are true, say so plainly — "This looks like it's still being figured out. Templating it now would encode the confusion. Worth workshopping first?" — and stop. Don't proceed to the interview on unsettled ground.

### Phase 2 — Interview

Ask targeted questions, one at a time. Cover only what discovery couldn't answer: judgment calls, tribal knowledge, intent. Interview length is proportional to discovery gaps — a well-trodden type of work produces a short interview; a novel type produces a longer one.

### Coverage Check

Before drafting, show a one-line coverage summary per section, flagging anything thin. User confirms or redirects. The agent owns "done," user owns the final confirm.

The bar: all five sections have enough material to be substantive. A new contributor should be able to produce a correct artifact from this template alone, without follow-up questions.

### Review Pass

Draft the template, summarize it conversationally (key contents, anything surprising), and take one round of feedback. Incorporate and close. Future refinement is editing the file directly or re-running the skill.

### Re-runs

Re-running the skill means re-running discovery against current artifacts and diffing against the existing template. Propose updates section by section. Never overwrite **Recurring Questions** or **Constraints** without explicit user confirmation — those are judgment calls, not inferred facts. **Settled Context** and **Pointers** can be updated from discovery alone.

## Output Document Structure

File path: `<output-dir>/<topic>/template-<pattern>.md` — no date prefix. Templates are living reference docs, not dated artifacts. If a workshop plan exists at `<output-dir>/<topic>/plan.md`, it should reference templates as pointers, not inline their content.

Sections:

- **What this is** — precise definition of this type of work in this specific project
- **Settled context** — conventions, patterns, file locations, existing decisions. Specification level: syntax, canonical form, edge cases. The stuff that never needs re-explaining.
- **Recurring questions** — the questions worth asking every time for this type of work. Written as actual questions ("What's the intended audience?"), not prose. This section is done when a new contributor could pick up the list and run a competent session without follow-up questions. If a question would itself prompt five clarifying questions, it's underspecified.
- **Constraints** — what's fixed, what can't be skipped, what must be considered
- **Pointers** — existing examples of this type of work. The "read these first" list.

## Principles

- **Specifications, not scaffolding.** Precise artifacts — syntax, convention, best practice stated at spec level. The discipline is in the output format, not the process.
- **Completeness is testable.** Would a new contributor produce a correct artifact from this alone? Fuzzy coverage isn't enough.
- **Define only, not instantiate.** This skill creates templates. Using them is the user's job.
- **Research first, interview second.** Discovery front-loads prior art inference so the interview is as short and targeted as possible.
- **One review pass, then done.** Not an open-ended loop. Interview + draft + one pass is the full session.
