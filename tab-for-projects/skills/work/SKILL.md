---
name: work
description: Autonomously execute ready tasks from the project backlog. Walks the dependency graph as a persistent loop, routes each task to the right subagent by category, keeps main-thread context small via ID-only dispatch, batches halts and new design tasks into a single end-of-run report, and invokes the shipper on any group with unshipped commits. Use when the backlog is groomed and the user wants to hand off execution. Triggers on `/work` and phrases like "finish the backlog", "execute the ready tasks", "work through the todo list".
argument-hint: "[optional: group_key, --max=N, --dry-run, --parallel]"
---

Hand over execution. The skill reads the ready portion of the backlog, routes each task to the appropriate subagent by category, walks the dependency graph as the subagents complete work, and produces a single end-of-run report covering what shipped, what got flagged, and what needs a user decision. It never executes below-bar tasks, never sets subagent task state on the subagent's behalf, and never silently "finishes" work that can't be verified.

## Trigger

**When to activate:**
- User invokes `/work`, optionally scoped to a `group_key` or limited by `--max=N`.
- User says "finish the backlog", "execute the ready tasks", "work through the todo list", "run the groomed tasks".
- User just finished `/backlog` and wants to cash in the groomed work.

**When NOT to activate:**
- Backlog hasn't been groomed — run `/backlog` first.
- User wants to file new work — use `/feature` or `/fix`.
- User wants to execute a single specific task with tight oversight — direct conversation is better than autonomous mode.

## Requires

- **MCP:** `tab-for-projects` — for project resolution, task reads, dependency-graph reads. `/work` does not set subagent task state; it reads state after subagents return.
- **Tool:** `Agent` — for dispatching to the subagent roster.
- **Tool:** `Bash`, `Read`, `Grep`, `Glob` — for working-tree inspection, git state, and validation. `/work` itself does not write code; subagents do.
- **Environment:** a git repo, clean working tree. If there are uncommitted changes, the skill stops and reports them before starting.

## Behavior

### 1. Resolve the project

Follow the shared Project Inference convention:

1. Explicit `project:<id or title>` argument wins.
2. Read `.tab-project` at repo root if present.
3. Parse git remote `origin`; exact repo-name match is high confidence.
4. Match cwd basename and parent segments against project titles.
5. Fall back to most recently updated plausible project. Never sole signal.

Below **confident**, ask. No writes below confident.

### 2. Build the initial plan

1. Pull all `todo` tasks for the project. Apply filters (`group_key`).
2. Pull the dependency graph.
3. For each task, evaluate readiness — a task is **ready** when all of the following hold: verb-led title; 1–3 sentence summary covering why + what; `effort`, `impact`, and `category` all set; a concrete acceptance signal (a test that must pass, an observable behavior change, an artifact produced, or an artifact removed); no unmet blocker dependencies. Partition into:
   - **Ready** — above the bar, no unmet blockers. Enters the eligible set.
   - **Flagged** — below the bar, or blocked by unready tasks. Include reason per task. Reported at end-of-run; never executed.
4. Topologically order the ready set by dependency edges, then by category priority (see routing table).
5. Respect `--max=N` if given. **No default cap** — `/work` is persistent and runs until the ready set is empty, the user interrupts, or three consecutive task failures abort the run.
6. Show the plan:

```
/work — Tab project
Ready: 7 tasks (persistent loop; no max cap)
Flagged: 3 tasks (see list at end)

Plan (first 5 shown; loop continues until ready set empty):
  1. 01KX… "Update README badges" (trivial / docs) → docs-writer
  2. 01KY… "Refactor session store" (medium / refactor) → implementer, reviewer after
  3. 01KZa… "MFA enrollment" (medium / feature, group auth-mfa) → architect, implementer, test-writer
  4. 01KZb… "MFA verification" (medium / feature, group auth-mfa) → architect, implementer, test-writer
  5. 01KZc… "MFA recovery" (low / feature, group auth-mfa) → implementer, test-writer
  ...

Proceed? (y / edit / dry-run)
```

Accept `edit` (user reorders or drops tasks), `dry-run` (prints plan only, no execution), or `--max=N` / `--parallel` flags.

### 3. Route each task to the right subagent

Task category determines the default agent. Optional precursor or successor agents form a chain that runs in sequence for a single task.

| Task category | Default agent | Optional precursor / successor                         |
| ------------- | ------------- | ------------------------------------------------------ |
| `feature`     | implementer   | architect (precursor, if effort ≥ medium); test-writer (successor) |
| `bugfix`      | implementer   | —                                                      |
| `refactor`    | implementer   | reviewer (successor)                                   |
| `test`        | test-writer   | —                                                      |
| `docs`        | docs-writer   | —                                                      |
| `perf`        | implementer   | —                                                      |
| `design`      | architect     | — (produces a doc, not code)                           |
| `security`    | reviewer      | implementer (successor, if fix needed)                 |
| `infra`       | implementer   | —                                                      |
| `chore`       | implementer   | —                                                      |

A chain is still one task. The precursor (e.g. architect for a medium-effort feature) files any design artifacts and notes, then the default agent picks up the same `task_id`. Successors run after the default agent marks `done`.

### 4. Dispatch contract — IDs only

`/work` **never** passes task prose to a subagent. The dispatch payload is:

- `task_id` — the task being worked. Always present.
- `parent_task_id` — the task that spawned this one, if chained (e.g. a rework routed back to implementer after a reviewer critical finding).
- `group_key` — only passed to the shipper at end-of-run.

Subagents fetch their own context via the MCP (`get_task`, `get_document`). `/work` does not mirror, summarize, or reformat task content. This is the mechanism that keeps the main thread's context window small across a long persistent run.

### 5. Status ceremony belongs to subagents

`/work` does not call `update_task` on dispatched tasks. Subagents own every transition:

- `in_progress` on claim
- `done` on verified completion
- `todo` with a specific note on failure or halt

After a subagent returns, `/work` re-reads task state to determine outcome:

| Subagent-returned state                           | `/work` response                                                                |
| ------------------------------------------------- | ------------------------------------------------------------------------------- |
| `done`                                            | Proceed. Fire the chained successor (if any), otherwise advance to next task.   |
| `todo` with "needs rework" note + reviewer findings | Re-dispatch to implementer with `parent_task_id` pointing at the reviewer task. |
| `todo` with "halt" note                           | Collect for end-of-run "needs your call" section. Advance to next task.         |
| Other `todo` (generic failure)                    | Counts against the three-strikes abort threshold. Advance to next task.         |

**On every subagent return, re-evaluate the dependency graph.** New tasks filed by the subagent, or completions that unblocked existing tasks, may expand the eligible set. Pull the graph again before picking the next task.

### 6. Halts and new design tasks are batched

`/work` does not interrupt the user mid-run. Throughout the loop:

- Halt notes accumulate in a queue.
- New tasks of category `design` filed by subagents (typically by the architect during a chain) accumulate in a separate queue — the user usually wants to weigh in on design forks before they spawn implementation work.
- All other status changes and new tasks flow without pause.

At end-of-run, both queues surface in the single "needs your call" section of the report.

### 7. Parallelism

Default: **serial**. Every task runs start-to-finish before the next one claims.

Opt-in: `--parallel` allows concurrent dispatch within a `group_key` when **all** of the following hold:

- Tasks share a `group_key`.
- No dependency edges exist between them.
- Task `context` either declares `parallel-safe` explicitly or the tasks touch different top-level directories (heuristic, not a guarantee).

Parallel dispatch spawns subagents via a single message with multiple `Agent` tool calls. On any return, re-evaluate the dependency graph before selecting the next batch. Parallelism is a safety valve for well-partitioned groups — the cost of a merge conflict or corrupted working tree is higher than the wall-clock savings most of the time.

### 8. End-of-run: invoke the shipper

Before producing the final report, for each `group_key` whose tasks completed during this run and whose commits haven't been shipped:

- Dispatch the `shipper` subagent with `{ group_key }`.
- The shipper derives the commit range from task ULIDs in commit messages, reads linked architect docs, and produces a PR description, release notes, or CHANGELOG polish.
- Shipper output flows into the end-of-run report. `/work` does not push, merge, or create PRs — the user ships.

### 9. Handle failure

If a task fails — acceptance signal doesn't pass, the subagent returns `todo`, the work reveals the task was below-bar after all:

- Subagent owns the failure note on the task.
- `/work` counts the failure against the three-strikes abort threshold.
- Advance to the next task.

**Abort conditions** (stop the whole run):

- Git working tree ends up in a dirty state `/work` can't clean up safely.
- Three consecutive task failures — something's wrong with the environment or the grooming.
- User interrupts.

When abort fires, skip directly to end-of-run reporting — the shipper step and the report structure still run for whatever completed successfully.

### 10. End-of-run report

```
/work complete — Tab project

Executed: 7 tasks · 5 commits · 3 new tasks filed by subagents

  ✓ 01KX… Update README badges                   → docs-writer
  ✓ 01KY… Refactor session store                 → implementer, reviewer (clean)
  ✓ 01KZa… MFA enrollment                        → architect, implementer, test-writer
  ✓ 01KZb… MFA verification                      → implementer, test-writer
  ✗ 01KZc… MFA recovery                          → implementer (halt — spec unclear)
  ✓ 01KW… Add security audit log                 → implementer
  ✗ 01KV… Upgrade cookie crypto                  → reviewer (halt — key rotation policy needed)

Flagged (3 tasks below bar — won't execute until groomed):
  01K1… "Improve search performance" — no acceptance signal
  01K2… "Investigate X" — blocked by 01K3… (also flagged)
  01K3… "Rethink Y" — no summary

Needs your call (2 halts · 1 new design task):
  01KZc "MFA recovery" halted — note: "recovery flow: SMS or TOTP-only? spec doesn't say"
  01KV "Upgrade cookie crypto" halted — note: "need key-rotation policy before touching AEAD"
  01KU "Choose MFA vendor" (new, category=design) — filed by architect during 01KZa

Shipper output:
  Group auth-mfa: 3 commits, PR description generated — see task 01KS for the draft.

Suggest: /backlog to address flagged items, then reply to the halts above.
```

## Output

- Commits on the current branch, one per completed task (subagents commit; `/work` does not).
- MCP state: subagents set completed tasks to `done`, failed/halted tasks to `todo` with notes. `/work` itself writes nothing to task records.
- New tasks filed by subagents appear in the backlog with `status: todo` and full readiness-bar fields.
- A single end-of-run report in the structure above.
- Optional: PR-description drafts or release-notes prose from the shipper, delivered as tasks the user can pick up or discard.

## Principles

- **The readiness bar is absolute.** A below-bar task is never executed, even if it looks doable. Flag and move on.
- **Verify, don't declare.** "Done" requires the acceptance signal to pass — and the subagent that did the work is the one that declares it.
- **IDs, not prose.** Every byte of task context that flows through the main thread is a byte the main thread has to carry. Let subagents fetch.
- **One task = one commit.** Subagents enforce this. If a run aborts halfway, the user gets a clean boundary to resume from.
- **Flagging is a feature, not a failure.** A run that executes 4 of 7 tasks and flags 3 with specific reasons is better than one that silently ships 7 half-done changes.
- **Halts are batched, never interruptive.** The user ran `/work` to hand off execution; breaking in for every design question defeats the handoff.
- **Parallelism has a cost.** Default serial. Opt in explicitly when the group is well-partitioned.

## Constraints

- **No writes below confident project inference.** Ask or stop.
- **No work on a dirty working tree.** The skill stops and asks before starting.
- **No setting task state on a subagent's behalf.** Status ceremony is the subagent's job.
- **No passing task prose to subagents.** IDs only — `task_id`, `parent_task_id`, `group_key`.
- **No mid-run interruption for halts.** Batch to end-of-run.
- **No force-push, no destructive git, no rewriting shared history.** Ever.
- **No executing below-bar tasks.** Ever. Flag instead.
- **No auto-merging PRs, no pushing commits.** The shipper produces drafts; the user ships.
- **Never skip acceptance-signal verification.** A task without verification is not done.
- **Three-strikes abort is non-negotiable.** Three consecutive failures means something structural is wrong — stop the run and hand it back.
