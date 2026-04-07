---
name: build
description: "Multi-task execution loop — implements ready tasks, reacts to blockers, captures knowledge."
argument-hint: "<task ID, or project ID to pick from ready tasks>"
mode: headless
agents:
  - tab-for-projects:project-manager
  - tab-for-projects:tech-lead
  - tab-for-projects:developer
requires-mcp:
  - tab-for-projects
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

### Execution Loop

2. **Pick the next task.** If the user specified a task, start there. Otherwise, take the next unblocked task from the ready list.

3. **Dispatch Developer** in a worktree (implementation mode) with:
   - `task_id`: the task to implement
   - `project_id`: the project ID
   - `document_ids`: IDs of relevant KB documents (search for docs matching the task's topic/group)
   - `domain_hint`: inferred from task context if obvious (frontend, backend, infrastructure, data)

   The Developer claims the task (`in_progress`), implements it, runs tests, commits, merges, marks it `done`, and returns an implementation report.

4. **Read the Developer's implementation report.** Branch based on the outcome:

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

   c. **Proceed to step 5.**

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
   c. Proceed to step 5.

5. **Check for next ready task.** Refresh the ready task list:
   ```
   get_ready_tasks({ project_id: "..." })
   ```

   Completing a task may have unblocked new ones (dependency resolution).

   - If ready tasks exist, loop back to step 2.
   - If no ready tasks remain (all done, all blocked, or none exist), exit the loop.

### Summary

6. **Present the build summary.**

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
- **Developer deviates from the plan:** Deviations are recorded in the implementation report. Surface them in the summary — they're information, not errors. The user should know when implementation diverged from the task plan.
- **Long-running loop:** There's no artificial limit on iterations. The loop runs until ready tasks are exhausted. The user can interrupt at any time.

## Future Enhancement

Parallel worktree dispatch — running multiple Developers simultaneously on independent tasks — is architecturally possible (worktrees provide isolation) but not implemented in this version. Start sequential, prove the loop, consider parallel later.
