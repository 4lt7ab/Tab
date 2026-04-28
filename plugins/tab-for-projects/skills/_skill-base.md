# Skill base — shared substrate

This file holds the contract every skill in `plugins/tab-for-projects/skills/` shares. Posture is per-skill (load-bearing per file — `/discuss`'s three-round shape, `/grind`'s worktree+merge discipline); this is the scaffolding both reuse, factored out so a fix to the contract doesn't have to thread two (or three, or four) files. Mirrors the discipline of `agents/_advisory-base.md` for advisors.

This file is NOT a skill. The leading underscore and the missing YAML frontmatter signal that to humans, to LLM authors writing new skills, and to the validator. Claude Code won't dispatch it (no `name` / `description` to gate on, and the file isn't named `SKILL.md`), and it has no skill body to dispatch with. It's a reference document, not a callable.

The Tab plugin runtime is markdown-only: no build step, no template engine, no include directive. So this substrate isn't *imported* anywhere — each skill file references it in prose, and the human (or LLM) authoring a new skill reads it here and writes the same contract into the new file. The factoring is for human / LLM-author consistency, not for runtime composition.

## Orchestrator framing

I'm an orchestrator. I read state, decide the next move, and act. The shape laid out in each skill's posture is the load-bearing contract; the timing of advisor calls, the parallelism strategy, and the round-by-round judgment are mine.

## Project resolution

Every skill resolves the project the same way:

> Explicit arg → `.tab-project` file → git remote → cwd. Refuse if ambiguous and name what would resolve it.

Ambiguity is a refusal, not a guess. Naming what would resolve it (e.g. *"pass `--project <id>`, or run from inside a checkout with a `.tab-project` file"*) is part of the refusal — the user shouldn't have to decode what the skill needed.

## Refusal conventions

Refusing is first-class. A skill refuses cleanly and says why; it doesn't half-run on bad input.

- **Missing or empty required input** — refuse immediately. Each skill names the input that's required (`/discuss` requires `<goal>`; `/grind` requires `<group_key>` and additionally refuses `"new"`). The framing is: *"I refuse on X. There's nothing to Y."*
- **Project ambiguous** — refuse and name what would resolve it (see above).
- **Input too vague to ground** — if the advisors come back with "I don't have enough to go on" across the board, halt and surface what the user needs to clarify. Don't fabricate.

## Halt vocabulary

The halt-condition vocabulary is shared across skills, even when individual skills only invoke a subset:

- **User interrupt** — every skill honors it. No exceptions.
- **Advisor unreachable** — retry once. If still down, the skill's own posture decides whether to proceed with the available advisors and surface the gap, or halt outright. Read-only skills tend to proceed-with-gap; writer skills lean toward halting.
- **Dirty working tree** — for any skill that writes to the host repo (`/grind` and any future writer). Read-only skills don't care about tree state.
- **Repeated failures** — for writer skills with a dispatch loop. The cap is the skill's call, but the principle is the same: three consecutive failures is diagnostic territory, not autopilot territory.
- **Merge content conflict** — for skills that merge. Never resolved autonomously; the user does.
- **Done** — every loop-shaped skill exits cleanly when the work it was given runs out (group done, plan synthesized, etc.).

When a skill halts, it prints what landed, what didn't, what the user should look at next. Silent halts are never acceptable.

## Read-only contract for advisors

When a skill calls an advisor, the advisor is read-only — see `agents/_advisory-base.md` for the full contract. The skill is the writer (when it writes at all). Advisors prescribe; skills act on the prescription. If a skill finds itself trying to coax an advisor into writing, that's a code smell — the skill should be writing the prescribed change itself.

## Output skeleton

Every skill's output names at minimum:

- The resolved `project_id`.
- A `halt_reason` (or its equivalent — `confidence` for read-only synthesis skills, an explicit halt enum for loop-shaped skills).
- A `next` line — one short suggestion for the user, so the skill chains naturally into whatever comes after it.

Skill-specific output fields layer on top — `/discuss` adds `plan` / `remaining_forks` / `participants`; `/grind` adds `landed` / `failed` / `friction_signals`. Those stay per-file.

## How to reference

In each posture-specific skill file, replace the verbatim shared clauses with:

> *See `_skill-base.md` for the shared orchestrator framing, project resolution, refusal conventions, and halt vocabulary. Skill-specific posture follows.*

Or a natural variation if the section flow calls for it. Then write only the posture-specific guidance — the round shape, the dispatch discipline, the specific arguments, the skill-specific output fields, the per-skill "what I write to / won't do / need".

If you find yourself writing a clause that already lives here, stop and reference instead. If you find yourself writing one that *should* live here but doesn't, propose adding it — substrate growth is fine, substrate drift across files is not.
