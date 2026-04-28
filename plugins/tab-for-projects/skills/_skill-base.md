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

## Worktree pre-flight for dispatched agents

Writer skills that dispatch sub-agents in isolated git worktrees (`isolation: "worktree"`) compensate for an upstream harness quirk: Claude Code anchors worktree creation to session-start HEAD, not current HEAD. A run that lands T1, T2, T3 and then dispatches T4 will hand T4 a worktree off the session-start commit — pre-T1, pre-T2, pre-T3. The dispatched agent reads the wrong file contents and writes against the wrong base, silently. We can't fix the harness from here, so writer skills compensate at the dispatch level.

**Pattern.** Every dispatched-agent prompt opens with a hard SHA pre-flight: the runner names the most recent host-main SHAs the agent's worktree should be able to reach (the merges/commits that have landed in this run plus a few from before it started), and instructs the agent to run `git log --oneline -N` first thing and verify every named SHA appears. The list is concrete commits the runner has just observed on host main, not a hash count or a date.

**Halt-and-report shape.** If any expected SHA is missing, the agent reports back exactly: *"pre-flight failed — worktree stale, missing SHAs: [list]"* and stops. The agent does **not** attempt recovery autonomously, does not read task files, does not start work. Recovery is the runner's call.

**Recovery path.** On a stale-worktree report, the runner sends a continuation message: *"Run `git fetch <host_repo_absolute_path> main && git rebase FETCH_HEAD`, then re-run `git log --oneline -N` and confirm the missing SHAs are now present. If recovery succeeds, proceed with the task."* The runner passes the host repo's absolute path; cross-worktree fetch needs it.

**Escape valve.** If `git fetch` or `git rebase` fails for any reason (sandbox blocks the fetch, rebase conflicts, anything), the agent halts again and reports the exact error. The runner handles it — re-dispatch off a refreshed base, or back off to the user. No autopilot recovery loop; two strikes and the runner steps in.

**Worked example.** SHA list shape (the runner inlines the SHAs it has just observed):

> The output **must contain all** of these commit SHAs:
> - `363eeb7` (the cli leaves a note)
> - `f2cee80` (merge: skills find a substrate)
> - `c0f314c` (skills get a base)
>
> If **any** are missing, halt and report: *"pre-flight failed — worktree stale, missing SHAs: [list]"*.

Continuation-message shape on stale report:

> Run `git fetch /Users/alttab/4lt7ab/Tab main && git rebase FETCH_HEAD`, then re-run `git log --oneline -10` and confirm the SHAs are present. If recovery succeeds, proceed. If fetch or rebase errors, halt and report the exact error.

## Output skeleton

Every skill's output names at minimum:

- The resolved `project_id`.
- A `halt_reason` (or its equivalent — `confidence` for read-only synthesis skills, an explicit halt enum for loop-shaped skills).
- A `next` line — one short suggestion for the user, so the skill chains naturally into whatever comes after it.

Skill-specific output fields layer on top — `/discuss` adds `plan` / `remaining_forks` / `participants`; `/grind` adds `landed` / `failed` / `friction_signals`. Those stay per-file.

## How to reference

In each posture-specific skill file, replace the verbatim shared clauses with:

> *See `_skill-base.md` for the shared orchestrator framing, project resolution, refusal conventions, halt vocabulary, and (for writer skills that dispatch into worktrees) the SHA pre-flight contract. Skill-specific posture follows.*

Or a natural variation if the section flow calls for it. Then write only the posture-specific guidance — the round shape, the dispatch discipline, the specific arguments, the skill-specific output fields, the per-skill "what I write to / won't do / need".

If you find yourself writing a clause that already lives here, stop and reference instead. If you find yourself writing one that *should* live here but doesn't, propose adding it — substrate growth is fine, substrate drift across files is not.
