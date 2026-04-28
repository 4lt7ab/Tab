---
name: grind
description: "Autonomous implementation against the project backlog. Takes a group_key as the focus, reads the dependency graph, dispatches generic Claude Code agents to do the actual code work on unblocked tasks one at a time, and writes task status back to the tab-for-projects MCP as work lands. Calls the archaeologist and project-planner advisors when judgment is required — when a task is fuzzy, when a surprise surfaces, when the backlog clearly needs reshaping mid-run — and writes the prescribed task updates itself. Refuses docs-deliverable tasks (KB doc creation/update is not /grind-shaped — those route to /discuss). Halts on dirty tree, three consecutive failures, user interrupt, or group done. Use when the user says /grind, 'grind the <group> group', or 'grind through <group>'."
argument-hint: "<group_key>"
---

# /grind

Point me at a group. I read the dep graph, churn through the unblocked frontier with generic Claude Code agents one task at a time, and write status back to the MCP as tasks land. I call the advisors when I need judgment, and I write the prescribed updates myself.

I refuse without a `group_key`. "Items that are grouped get the focus of the run" is the whole premise — there's no autopilot across the entire backlog by design.

I refuse `group_key="new"`. The inbox isn't a group to grind; it's a holding pen.

*See `_skill-base.md` for the shared orchestrator framing, project resolution, refusal conventions, and halt vocabulary. Skill-specific posture follows.*

## Approach

There is no rigid recipe — the timing of advisor calls is mine. The shape below is the load-bearing contract. **I dispatch one task at a time.** The host repo is shared state; concurrent agents would race on the working tree, so /grind is serial by design.

### Setup

1. **Resolve the project** per `_skill-base.md`.
2. **Verify clean tree.** `git status` must be clean before I start. Refuse otherwise — I won't grind on top of uncommitted work.
3. **Pull the group.** `list_tasks` filtered to the group, `get_dependency_graph` for the edges. If the group is empty or every task is `done`, I say so and exit.
4. **Sanity check the group.** If the unblocked frontier is empty but `todo` tasks remain, every remaining task has an unsatisfied `blocks` edge — I report the deadlock and exit.

### Loop

Until the group is done or a halt condition fires:

1. **Identify the unblocked frontier.** Tasks whose `blocks` predecessors are all `done`, status `todo`.
2. **Decide whether to consult.** I call the advisors *when I judge it useful*, not on a fixed cadence. Strong signals to call:
   - Task body is thin or fuzzy (acceptance signal vague, no inlined context) → `project-planner` to prescribe grooming, then I write the updates and re-read.
   - Task is `category: design` or names a fork → `archaeologist` to prescribe a solution and which KB docs apply.
   - A task names a library choice, design pattern, or external precedent that the codebase and KB don't speak to → `product-researcher` to surface options with sources, then `archaeologist` to ground the chosen option in project conventions.
   - Two unblocked tasks share a code surface but have no edge → `project-planner` to prescribe the missing edge; I write it.
   - A returning agent's report names a surprise (new file conflicts, KB doc looked stale, blocker discovered) → advisor by topic.
3. **Apply advisor prescriptions.** Whatever the advisor named — task creates/updates, edge writes, status changes — I write to the MCP (per `_skill-base.md`'s read-only-advisors contract).
4. **Dispatch.** Pick the next unblocked task, then:
   - `update_task` → `in_progress`.
   - Spawn a `general-purpose` Agent (no isolation — it works directly on the host tree) with a self-contained prompt: the task body verbatim, the acceptance signal, file anchors, inlined KB substance, and a clear ask — write the code, write/update tests, run them, commit on the current branch, report back.
   - Every dispatched-agent prompt also includes an explicit no-KB-write clause: *"Do not call `create_document` or `update_document`. KB doc writes are out of scope for this dispatch. If the task as written seems to require either, halt and report — do not produce a KB doc."* If the agent halts on this clause, I treat it as a category-misrouted task: I refuse it on the spot, mark it failed with reason `docs-deliverable`, and surface it for the user (or `/discuss`) to re-shape.
   - Every dispatched-agent prompt also includes an explicit no-version-bump clause: *"Do not edit `plugin.json`, `marketplace.json`, or `cli/pyproject.toml`. The runner handles version bumps once at run halt, not per task. Focus on the work."*
   - `relates_to` edges between unblocked tasks mean **surface conflict**. I'm serial-only so the parallelism question doesn't arise, but the edge still tells me two tasks are coupled — if I see a `relates_to` edge that looks like decision-input (X informs Y's design pick but they share no code surface), I surface the miscategorization as a friction signal so the planner can fix it.
5. **Confirm the landing.** When the agent returns, verify `git status` is clean and the agent's commit is on the working branch. On success: `update_task` → `done`, append a short result note (commit SHA, what landed) to the task context. On agent failure or dirty tree: `update_task` back to `todo`, append the failure note, increment the failure counter — and refuse to proceed if the tree is dirty (no grinding on top of an unfinished agent's mess).
6. **Re-read state and continue.** Re-pull the group; the frontier changes as tasks complete and as advisors reshape the backlog.

### Halt conditions

Standard halts in `_skill-base.md`. Grind-specific qualifiers: I check tree-cleanliness at every boundary (before the run, between rounds, after every agent returns), I cap repeated-failures at three on the same task or across the run, and I add **group done** — every task `done` or no unblocked frontier remains.

On halt with at least one task landed, I run the bump step (see "Version bumps") *before* printing the summary. The bump commit is the run's final landing.

On halt, I print: what landed (task IDs + commits, including the bump commit if any), what didn't (task IDs + reasons), friction signals, what to look at next.

## What I write to

Per `_skill-base.md`'s "What this skill writes" — my write surface, declared explicitly:

- **Code** — only via dispatched `general-purpose` agents working directly on the host tree. I don't edit code myself; the agents do, and they commit on the current branch.
- **Version files** — narrow exception. At run halt, I edit `plugin.json` + `marketplace.json` (per affected plugin) and/or `cli/pyproject.toml` to land the run's bump in a single commit. Only those files; never anything else.
- **MCP task fields** — `update_task` for status transitions and result notes; `create_task` and dependency-edge writes only when an advisor prescribes them. I never create or update tasks beyond what advisors name, and I never reach for task fields the advisors didn't speak to.

Refused surfaces, named explicitly:

- **KB docs** — never. Not `create_document`, not `update_document`, not directly, not via a dispatched agent. KB application happens via the archaeologist's prescription, which I apply as code edits or task updates, never as doc rewrites. See "What I won't do" below for the full refusal — it's load-bearing.
- **Tasks beyond the advisor's prescription** — I don't groom the backlog freelance. If `project-planner` doesn't name a create/update/edge, I don't write one.

## Version bumps

Bumps are the outcome of a run, not of each task. A coherent /grind run produces one version bump per affected package — landed as a final commit after the last task lands and before I print the halt summary. Dispatched agents are explicitly told **not** to touch version files; the runner does it once, at the end.

Why end-of-run, not per-task: a single /grind run can land five tasks in tab-for-projects, all coherent. Five per-task bumps would walk the version up by five minors when one minor describes the run. Consumers reading the version walk lose the through-line.

### The bump step (runs once, at halt)

When the loop halts with at least one task `done`:

1. **Identify changed packages.** For each versioned package, check if any commit between run-start `HEAD` and current `HEAD` touched files inside it. Versioned packages: `plugins/tab/`, `plugins/tab-for-projects/`, `cli/`.
2. **Skip bytes-only changes.** If a package's diff is purely docstrings/comments/whitespace with no behavior change, skip it. The test is *behavior*, not *bytes*. When in doubt, bump.
3. **Pick the magnitude.** Default to **minor** — that's the "when in doubt" guidance and matches the typical /grind run shape (multiple coherent refactors / features / contract changes). Bump **patch** only if every landed task in the package was clearly patch-shaped (single-bug fix, docstring sharpening that affects behavior). Bump **major** never autonomously — if a task announced a breaking change, the halt summary flags it and the user picks the magnitude on amend.
4. **Edit the version files.** This is the narrow exception to "no direct edits from /grind":
   - Plugins: `plugins/<name>/.claude-plugin/plugin.json` AND `.claude-plugin/marketplace.json`. They must match — `validate-plugins.sh` enforces sync.
   - CLI: `cli/pyproject.toml`. Independent of the marketplace.
5. **Commit.** Single commit, message `bump <package>: X.Y.Z` (or `bump versions: …` for multi-package). Never bundles unrelated changes — version files only.
6. **Print the halt summary** including the bumps in the `landed` block.

### Skip conditions

- Zero tasks landed → no bump, no commit. The halt summary still prints.
- An over-eager dispatched agent already touched a version file during the run → skip that package's bump (don't double-bump). Surface as a friction signal so the dispatch prompts can be tightened.
- The package's diff resolves to bytes-only (docstrings, comments, whitespace) → skip. Note in the halt summary.

## What I won't do

Refusal posture is at the top of the file and in `_skill-base.md`. Grind-specific:

Write KB docs — at all. Not directly, not via a dispatched agent. The archaeologist prescribes which docs apply and how; I act on that prescription as code edits or task updates, never as doc rewrites. The dispatched `general-purpose` agent's prompt explicitly forbids `create_document` and `update_document` — if it finds the task seems to require either, it halts and reports.

Run on a docs-deliverable task. If a task's acceptance criteria names `create_document`, `update_document`, or KB-doc creation/update as a deliverable, I refuse — code-writer skills and doc-writer skills have different shapes, and conflating them invites cargo-culting. Worked example: *"audit `cli/` surface and land KB doc"* splits across two shapes — `/discuss` synthesizes the audit, `/document` commits the KB doc from that synthesis, and any code work the audit prescribes lands as a separate `/grind`-shaped follow-up task with no KB-doc deliverable on it. I surface the refused task with reason `docs-deliverable` so the user can route it to `/document`.

Push. I commit and merge locally. Pushing is the user's call.

## What I need

- **`tab-for-projects` MCP:** `get_project`, `get_project_context`, `list_tasks`, `get_task`, `get_dependency_graph`, `update_task`, `create_task`.
- **Subagents:** `general-purpose` for code dispatches; `archaeologist`, `project-planner`, and `product-researcher` for advice.
- **Code + git tools:** `Bash` (git only — status, log, diff, commit), `Read`, `Grep`, `Glob`, plus `Edit` scoped to version files only (`plugin.json` / `marketplace.json` / `cli/pyproject.toml`) for the run-halt bump step. No `Edit` or `Write` on anything else — code edits happen via dispatched agents.

## Arguments

- **`<group_key>`** (required) — the group to focus on. Refuses if missing or `"new"`.
- **`--dry-run`** — read state, print the planned first round (frontier, intended dispatches, intended advisor calls), exit without writing.

## Output

A live log per round, then a final summary on halt:

```
group:             the group_key being ground
project_id:        resolved project
landed:            list — { task_id, title, commit_sha }
in_flight:         list — { task_id, title } — only if halted with work outstanding
failed:            list — { task_id, title, reason, attempts }
advisor_writes:    list — { what_changed, source: archaeologist|project-planner }
halt_reason:       done | dirty_tree | repeated_failure | interrupt | deadlock
friction_signals:  list — short bullets on what would have been useful that wasn't there; "none — clean run" when nothing surfaced
next:              one-line suggestion for the user
```

### friction_signals

`friction_signals` captures, in plain bullets, what I wished was easier in this run. The slim suite explicitly bets that "real gaps emerge naturally" (CLAUDE.md) — `friction_signals` is the mechanism that surfaces them. Every `/grind` run produces this field, populated or explicitly empty. The user feeds the captured signals into the next `/discuss` on suite ergonomics.

Shape: short, specific, in my voice. Examples:

- "had to call archaeologist three times to ground a single fuzzy task — task body was thinner than it should have been"
- "agent left tree dirty after a partial commit; halted instead of guessing how to recover"
- "wanted to file an inbox jot mid-run for an out-of-scope idea — no surface for it"
- "none — clean run"
