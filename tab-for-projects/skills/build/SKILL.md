---
name: build
description: "Multi-task execution loop — implements ready tasks, reacts to blockers, captures knowledge. Use when the user wants to build, implement tasks, or invokes /build."
argument-hint: "<task ID, or project ID to pick from ready tasks>"
---

# Build — Multi-Task Execution Loop

The execution play. The crown jewel. Picks up ready tasks, dispatches the Developer in worktrees to implement them, reacts to blockers by spawning support agents, captures emerging knowledge after significant completions, and keeps going until the work is done or a human is needed. This is Tab playing the game — not just dispatching, but reading the board and making moves.

## Trigger

**When to activate:**
- The user runs `/build`
- The user says "start building" or "implement the next tasks"

**When NOT to activate:**
- The user wants to plan work first (that's `/plan`)
- The user wants a status check (that's `/status`)
- The user wants to investigate code without implementing (that's `/investigate`)

## Arguments

- **Task ID:** Start with this specific task. Skip task selection.
- **Project ID or title:** Pick from that project's ready tasks.
- **No argument:** If only one project exists, use it. Otherwise, list projects and ask.

## Sequence

### Setup

1. **Resolve the target.** If a task ID was provided, fetch it and confirm it's ready (not blocked, not done). If a project was provided (or resolved), check ready tasks:
   ```
   get_ready_tasks({ project_id: "..." })
   ```
   If no tasks are ready, exit immediately and tell the user — suggest `/plan` to create tasks or `/status` to diagnose blockers.

2. **Group tasks by codebase affinity.** Read each ready task's description, plan, and group field. Cluster tasks that will touch the same areas of the codebase — same module, same subsystem, same files. The goal: a developer who scans an area once can implement several tasks there without rescanning.

   Grouping heuristics (in priority order):
   - **Explicit group match** — tasks with the same `group` field belong together.
   - **File overlap** — tasks whose plans reference the same files or directories.
   - **Domain affinity** — tasks in the same domain (frontend, backend, infrastructure, data) that lack stronger signals.
   - **Dependency chains** — if task B depends on task A and both are ready, group them so the same developer handles A then B without context loss.

   A single task that doesn't cluster with anything is its own group of one — that's fine.

   **Group size limit:** Cap at 4-5 tasks per group. Beyond that, context bloat outweighs the scanning savings.

### Execution Loop

3. **Pick the next group.** Take the next task group from the grouped list. If the user specified a single task ID, skip grouping — it's a group of one.

4. **Dispatch Developer** in a worktree (implementation mode) with:
   - `task_ids`: the list of task IDs in this group (ordered by dependency, then effort — lightest first)
   - `project_id`: the project ID
   - `document_ids`: IDs of relevant KB documents (search for docs matching the group's topic area)
   - `domain_hint`: inferred from task context if obvious (frontend, backend, infrastructure, data)

   The Developer claims all tasks (`in_progress`), implements them sequentially within a single session (benefiting from shared codebase context), runs tests, commits, merges, and returns an implementation report covering all tasks in the group.

5. **Read the Developer's implementation report.** The report contains a per-task breakdown. Branch based on each task's outcome:

   ### If `done` — Success Path

   a. **Check for knowledge capture.** If ALL of these are true:
      - The completed task had **medium or higher effort**
      - The Developer's report flags **new conventions or patterns** in the `follow_up` or `deviations` fields

      Then **dispatch Tech Lead** with:
      - `project_id`: the project ID
      - `dispatch_type`: `write` or `update` (search KB first to decide)
      - `scope`: the convention or pattern discovered
      - `context`: the Developer's implementation report — findings, file references, what's new

      Read the TL report. Note any documents created or updated.

   b. **Check for follow-up work.** If the Developer's report includes items in `follow_up`:
      - Collect them. Do NOT create tasks automatically.
      - Surface them in the final summary for the user to decide on.

   c. **Proceed to step 6.**

   ### If `blocked` — Support Path

   a. **Analyze the blocker.** Read the `blockers` field in the Developer's report.

   b. **Route to the appropriate support agent:**

      **Missing KB docs, design context, or architectural guidance →** Dispatch Tech Lead with:
      - `project_id`: the project ID
      - `dispatch_type`: `write`
      - `scope`: the topic the Developer needs documentation on
      - `context`: the Developer's blocker description, what's missing, what questions need answering

      **Missing requirements, unclear acceptance criteria, or task ambiguity →** Dispatch Project Manager with:
      - `project_id`: the project ID
      - `focus`: `task-shape`
      - `task_ids`: [the blocked task's ID]

      **Needs human decision (ambiguous scope, conflicting requirements, judgment call) →** Do not dispatch another agent. Surface the blocker to the user in the summary. Move to the next task.

   c. **After support resolves, re-dispatch Developer** for the same task with the same input. The support agent should have filled the gap. If the Developer reports blocked again on the same issue, surface it to the user and move on.

   ### If `failed` — Failure Path

   a. Record the failure reason.
   b. Do not retry. Surface the failure in the summary.
   c. Proceed to step 6.

6. **Check for next group.** If groups remain in the current batch, loop back to step 3. If all groups are exhausted, refresh the ready task list:
   ```
   get_ready_tasks({ project_id: "..." })
   ```

   Completing tasks may have unblocked new ones (dependency resolution). If new ready tasks appear, re-group them (step 2) and continue. If no ready tasks remain (all done, all blocked, or none exist), exit the loop.

### Summary

7. **Present the build summary.**

## Output

**Tasks completed** — Table of tasks implemented this run: ID, title, approach summary, files changed. Ordered by completion.

**Blockers hit** — Tasks that blocked and how they were resolved (or not). Which support agents were dispatched, what they did.

**Knowledge captured** — KB documents created or updated during the run, with titles and what they cover.

**Follow-up work discovered** — Items flagged by the Developer during implementation that aren't captured as tasks yet. These are suggestions for the user, not commitments.

**What's next** — Remaining ready tasks (if the loop exited with work still available), or "all tasks complete" if the project is done. If everything is blocked, explain what's blocking progress.

## Edge Cases

- **No ready tasks at start:** Exit immediately. Tell the user nothing is ready to build. Suggest `/status` to diagnose or `/plan` to create work.
- **All tasks block:** After attempting support resolution for each, exit the loop. The summary should clearly explain what's stuck and why. Multiple tasks blocking on the same issue is a signal worth surfacing.
- **Single task specified but it's blocked:** Don't silently pick another task. Tell the user their requested task is blocked, explain why, and ask if they want to build other ready tasks instead.
- **Only one ready task:** Skip grouping. It's a group of one.
- **Tasks span unrelated areas:** Don't force them into a group. Two unrelated tasks in separate groups (each with one developer) is better than one bloated group where the developer loses focus.
- **Developer deviates from the plan:** Deviations are recorded in the implementation report. Surface them in the summary — they're information, not errors. The user should know when implementation diverged from the task plan.
- **Long-running loop:** There's no artificial limit on iterations. The loop runs until ready tasks are exhausted. The user can interrupt at any time.

## Future Enhancement

Parallel worktree dispatch — running multiple Developer groups simultaneously in separate worktrees — is architecturally possible (worktrees provide isolation, groups are independent by design) but not implemented in this version. The current model dispatches groups sequentially. Parallel dispatch is the natural next step once the grouping model is proven.
