---
name: work
description: Autonomously execute ready tasks from the project backlog. Walks the dependency graph, spawns subagent teams for parallel work, verifies acceptance signals, commits per task, and flags tasks that fall below the readiness bar instead of guessing. Use when the backlog is groomed and the user wants to hand off execution. Triggers on `/work` and phrases like "finish the backlog", "execute the ready tasks", "work through the todo list".
argument-hint: "[optional: group_key, --max=N, --dry-run]"
---

Hand over execution. The skill reads the ready portion of the backlog, builds an execution plan, runs tasks (serial or via subagent teams), verifies each one against its acceptance signal, and reports what got done and what got flagged. It never executes below-bar tasks and never silently "finishes" work that can't be verified.

## Trigger

**When to activate:**
- User invokes `/work`, optionally scoped to a `group_key` or limited by `--max=N`.
- User says "finish the backlog", "execute the ready tasks", "work through the todo list", "run the groomed tasks".
- User just finished `/backlog` and wants to cash in the groomed work.

**When NOT to activate:**
- Backlog hasn't been groomed — run `/backlog` first.
- User wants to file new work — use `/plan-project` or `/fix`.
- User wants to execute a single specific task with tight oversight — direct conversation is better than autonomous mode.

## Requires

- **MCP:** `tab-for-projects` — for project resolution, task reads/writes, dependency graph.
- **Tool:** `Bash`, `Edit`, `Write`, `Read`, `Grep`, `Glob` — for actual code work.
- **Tool:** `Agent` — for spawning subagent teams on parallelizable tasks.
- **Tool (preferred):** `exa` MCP — for research during execution.
- **Environment:** a git repo, clean working tree. If there are uncommitted changes, the skill stops and reports them before starting.

## Behavior

### 1. Resolve the project

Resolve which project this run targets:

1. Explicit `project:<id or title>` argument wins.
2. Read `.tab-project` at repo root if present.
3. Parse git remote `origin`; exact repo-name match is high confidence.
4. Match cwd basename and parent segments against project titles.
5. Fall back to most recently updated plausible project. Never sole signal.

Below **confident**, ask. No writes below confident.

### 2. Build the execution plan

1. Pull all `todo` tasks for the project. Apply filters (`group_key`).
2. Pull the dependency graph.
3. For each task, evaluate readiness — a task is **ready** when all of the following hold: verb-led title; 1–3 sentence summary covering why + what; `effort`, `impact`, and `category` all set; a concrete acceptance signal (a test that must pass, an observable behavior change, an artifact produced, or an artifact removed); no unmet blocker dependencies. Partition into:
   - **Ready** — above the bar, no unmet blockers.
   - **Flagged** — below the bar, or blocked by unready tasks. Include reason per task.
4. Topologically order the ready set. Tasks in the same `group_key` with no ordering edges between them are candidates for parallel execution.
5. Respect `--max=N` if given. Default max: 5 tasks per invocation. This is a safety valve, not a suggestion.
6. Show the plan:

```
/work — Tab project
Ready: 7 tasks (4 serial, 3 parallel in group auth-mfa)
Flagged: 3 tasks (see list at end)
Will execute: 5 (--max=5; 2 deferred)

Plan:
  1. 01KX… "Update README badges" (trivial / docs)
  2. 01KY… "Refactor session store" (medium / refactor)
  3–5. [parallel] 01KZa… 01KZb… 01KZc… (group auth-mfa)

Proceed? (y / edit / dry-run)
```

Accept `edit` (user reorders or drops tasks) or `dry-run` (prints plan only, no execution).

### 3. Execute

For each task in plan order:

1. Mark task `in_progress` via `update_task`.
2. **Serial task** — execute in the main session. Read the task context, do the work, verify acceptance signal.
3. **Parallel group** — spawn subagents via `Agent` tool, one per task, each with the task's full context and the acceptance signal it must meet. Run in parallel.
4. Verify the acceptance signal:
   - Test? Run it. Must pass.
   - Behavior? Demonstrate (preview tools, logs, whatever the signal specifies).
   - Artifact? Check it exists and meets the described shape.
5. Commit per task. One task = one commit. Conventional commit style, title references the task title, body references the task ULID.
6. Mark task `done`. Move to next.

**On subagent completion:** re-check readiness of remaining tasks. A task previously blocked by the one just completed may now be ready — it moves into the eligible set for the remainder of this run.

### 4. Handle failure

If a task fails — acceptance signal doesn't pass, a dependency breaks, the work reveals the task was below-bar after all:

- Revert task to `todo`.
- Add a note to the task's context explaining what went wrong.
- Move it to the flagged list.
- Continue with the next task. Don't abort the whole run on one failure.

**Abort conditions** (stop the whole run):
- Git working tree ends up in a dirty state the skill can't clean up safely.
- Three consecutive task failures — something's wrong with the environment or the grooming.
- User interrupts.

### 5. Report

At the end:

```
/work complete — Tab project

Executed: 5 tasks (3 commits on main, 2 failed)
  ✓ 01KX… Update README badges
  ✓ 01KY… Refactor session store
  ✓ 01KZa… [parallel] MFA enrollment
  ✗ 01KZb… [parallel] MFA verification — acceptance test failed (see task notes)
  ✗ 01KZc… [parallel] MFA recovery — subagent flagged: spec unclear

Flagged (5 tasks won't execute until groomed):
  01K1… "Improve search performance" — no acceptance signal
  01K2… "Investigate X" — blocked by 01K3… (also flagged)
  ...

Suggest: /backlog to address flagged items.
```

## Output

Commits on the current branch, one per completed task. MCP state updated: completed tasks `done`, failed tasks `todo` with notes. A closing report like the above.

## Principles

- **The readiness bar is absolute.** A below-bar task is never executed, even if it looks doable. Flag and move on.
- **Verify, don't declare.** "Done" requires the acceptance signal to pass. No signal = no claim of done.
- **Small, reversible commits.** One task per commit. If the run fails halfway, the user gets a clean boundary to resume from.
- **Flagging is a feature, not a failure.** A run that executes 4 of 7 tasks and flags 3 with specific reasons is better than one that silently ships 7 half-done changes.
- **Parallelism has a cost.** Only parallelize within a `group_key` where tasks genuinely don't share files. When in doubt, serial.

## Constraints

- **No writes below confident project inference.** Ask or stop.
- **No work on a dirty working tree.** The skill stops and asks before starting.
- **No force-push, no destructive git, no rewriting shared history.** Ever.
- **No executing below-bar tasks.** Ever. Flag instead.
- **No auto-merging PRs.** The skill may propose a PR at the end; the user decides.
- **Max task count is a hard cap.** Respect `--max=N` or the default of 5. Don't drift past it "because we're on a roll."
- **Never skip the acceptance-signal verification step.** A task without verification is not done.
