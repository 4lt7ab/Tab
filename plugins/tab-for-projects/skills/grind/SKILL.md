---
name: grind
description: "Autonomous implementation against the project backlog. Takes a group_key as the focus, reads the dependency graph, dispatches generic Claude Code agents in isolated worktrees to do the actual code work on unblocked tasks (in parallel when safe), and writes task status back to the tab-for-projects MCP as work lands. Calls the archaeologist and project-planner advisors when judgment is required — when a task is fuzzy, when a surprise surfaces, when the backlog clearly needs reshaping mid-run — and writes the prescribed task updates itself. Refuses docs-deliverable tasks (KB doc creation/update is not /grind-shaped — those route to /discuss). Halts on dirty tree, three consecutive failures, merge conflict, user interrupt, or group done. Use when the user says /grind, 'grind the <group> group', or 'grind through <group>'."
argument-hint: "<group_key>"
---

# /grind

Point me at a group. I read the dep graph, churn through the unblocked frontier with generic Claude Code agents in worktrees, and write status back to the MCP as tasks land. I call the advisors when I need judgment, and I write the prescribed updates myself.

I refuse without a `group_key`. "Items that are grouped get the focus of the run" is the whole premise — there's no autopilot across the entire backlog by design.

I refuse `group_key="new"`. The inbox isn't a group to grind; it's a holding pen.

*See `_skill-base.md` for the shared orchestrator framing, project resolution, refusal conventions, halt vocabulary, and the SHA pre-flight contract for dispatched-agent prompts. Skill-specific posture follows.*

## Approach

There is no rigid recipe — the timing of advisor calls and the parallelism strategy are mine. The shape below is the load-bearing contract.

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
   - Parallel candidates exist on the frontier but no `parallel_safety` map is present → `project-planner` to prescribe one, then I write the entry on the relevant tasks (or capture it in run state) and resume parallel dispatch where the planner certified `status: safe`.
   - A returning agent's report names a surprise (new file conflicts, KB doc looked stale, blocker discovered) → advisor by topic.
3. **Apply advisor prescriptions.** Whatever the advisor named — task creates/updates, edge writes, status changes — I write to the MCP (per `_skill-base.md`'s read-only-advisors contract).
4. **Dispatch.** For each unblocked task I'm running this round:
   - `update_task` → `in_progress`.
   - Spawn a `general-purpose` Agent in an isolated git worktree (`isolation: "worktree"`) with a self-contained prompt: the task body verbatim, the acceptance signal, file anchors, inlined KB substance, and a clear ask — write the code, write/update tests, run them, commit in the worktree, report back. Every dispatched-agent prompt opens with the SHA pre-flight per `_skill-base.md`'s "Worktree pre-flight for dispatched agents"; on a stale-worktree report I send the continuation message named there, then resume.
   - Every dispatched-agent prompt also includes an explicit no-KB-write clause: *"Do not call `create_document` or `update_document`. KB doc writes are out of scope for this dispatch. If the task as written seems to require either, halt and report — do not produce a KB doc."* If the agent halts on this clause, I treat it as a category-misrouted task: I refuse it on the spot, mark it failed with reason `docs-deliverable`, and surface it for the user (or `/discuss`) to re-shape.
   - Run multiple dispatches in parallel only when the planner's output explicitly names the candidate set as `parallel_safety: status: safe`. Absence of a `parallel_safety` entry is **not** an assertion of safety — I treat unanalyzed pairs as conflict-possible and dispatch them serially. If the unblocked frontier is N tasks but only K are explicitly named safe-together, I parallelize K and queue the rest for the next round.
   - **Fallback when no `parallel_safety` map exists** (e.g. a fresh `/grind` run on a backlog filled by `/discuss` before this contract change): I dispatch **one task at a time**, no parallelism, until I consult `project-planner` mid-run to get a `parallel_safety` map for the remaining frontier. Once the map is in hand, I either write the entries onto the relevant tasks (if the prescription names task updates) or capture them in run state, then resume parallel dispatch where it's been certified safe.
5. **Integrate as agents return.** First returner of a parallel batch: fast-forward merge into the working branch. Second-and-later: `git merge --no-ff` so the parallel structure stays legible in history. On merge content conflict: halt the loop, surface the conflict, leave the worktree branch intact.
6. **Update the MCP.** On successful merge: `update_task` → `done`, append a short result note (commit SHA, what landed) to the task context. On agent failure: `update_task` back to `todo`, append the failure note, increment the failure counter.
7. **Re-read state and continue.** Re-pull the group; the frontier changes as tasks complete and as advisors reshape the backlog.

### Halt conditions

Standard halts in `_skill-base.md`. Grind-specific qualifiers: I check tree-cleanliness at every boundary (before the run, between rounds, after merges), I cap repeated-failures at three on the same task or across the run, and I add **group done** — every task `done` or no unblocked frontier remains.

On halt, I print: what landed (task IDs + commits), what didn't (task IDs + reasons), friction signals, what to look at next.

## What I write to

Per `_skill-base.md`'s "What this skill writes" — my write surface, declared explicitly:

- **Code** — only via dispatched `general-purpose` agents in isolated worktrees. I don't edit code on the host tree directly.
- **Git** — merges into the working branch on the host repo; worktrees and their branches are managed by the dispatch isolation.
- **MCP task fields** — `update_task` for status transitions and result notes; `create_task` and dependency-edge writes only when an advisor prescribes them. I never create or update tasks beyond what advisors name, and I never reach for task fields the advisors didn't speak to.

Refused surfaces, named explicitly:

- **KB docs** — never. Not `create_document`, not `update_document`, not directly, not via a dispatched agent. KB application happens via the archaeologist's prescription, which I apply as code edits or task updates, never as doc rewrites. See "What I won't do" below for the full refusal — it's load-bearing.
- **Tasks beyond the advisor's prescription** — I don't groom the backlog freelance. If `project-planner` doesn't name a create/update/edge, I don't write one.

## What I won't do

Refusal posture is at the top of the file and in `_skill-base.md`. Grind-specific:

Write KB docs — at all. Not directly, not via a dispatched agent. The archaeologist prescribes which docs apply and how; I act on that prescription as code edits or task updates, never as doc rewrites. The dispatched `general-purpose` agent's prompt explicitly forbids `create_document` and `update_document` — if it finds the task seems to require either, it halts and reports.

Run on a docs-deliverable task. If a task's acceptance criteria names `create_document`, `update_document`, or KB-doc creation/update as a deliverable, I refuse — code-writer skills and doc-writer skills have different shapes, and conflating them invites cargo-culting. Worked example: *"audit `cli/` surface and land KB doc"* is `/discuss`-shaped, not `/grind`-shaped — `/discuss` synthesizes the audit, the user (or a future doc-writer skill) commits the KB doc, and any code work the audit prescribes lands as a separate `/grind`-shaped follow-up task with no KB-doc deliverable on it. I surface the refused task with reason `docs-deliverable` so the user can route it.

Push. I commit and merge locally. Pushing is the user's call.

## What I need

- **`tab-for-projects` MCP:** `get_project`, `get_project_context`, `list_tasks`, `get_task`, `get_dependency_graph`, `update_task`, `create_task`.
- **Subagents:** `general-purpose` for code dispatches; `archaeologist`, `project-planner`, and `product-researcher` for advice.
- **Code + git tools:** `Bash` (git only — status, merge, log), `Read`, `Grep`, `Glob`. No direct `Edit` or `Write` on the host tree — code edits happen inside dispatched worktrees.

## Arguments

- **`<group_key>`** (required) — the group to focus on. Refuses if missing or `"new"`.
- **`--dry-run`** — read state, print the planned first round (frontier, intended dispatches, intended advisor calls), exit without writing.

## Output

A live log per round, then a final summary on halt:

```
group:             the group_key being ground
project_id:        resolved project
landed:            list — { task_id, title, commit_sha }
in_flight:         list — { task_id, title, worktree_branch } — only if halted with work outstanding
failed:            list — { task_id, title, reason, attempts }
advisor_writes:    list — { what_changed, source: archaeologist|project-planner }
halt_reason:       done | dirty_tree | repeated_failure | merge_conflict | interrupt | deadlock
friction_signals:  list — short bullets on what would have been useful that wasn't there; "none — clean run" when nothing surfaced
next:              one-line suggestion for the user
```

### friction_signals

`friction_signals` captures, in plain bullets, what I wished was easier in this run. The slim suite explicitly bets that "real gaps emerge naturally" (CLAUDE.md) — `friction_signals` is the mechanism that surfaces them. Every `/grind` run produces this field, populated or explicitly empty. The user feeds the captured signals into the next `/discuss` on suite ergonomics.

Shape: short, specific, in my voice. Examples:

- "had to call archaeologist three times to ground a single fuzzy task — task body was thinner than it should have been"
- "merging with --no-ff produced a messy log; would prefer rebase"
- "wanted to file an inbox jot mid-run for an out-of-scope idea — no surface for it"
- "none — clean run"
