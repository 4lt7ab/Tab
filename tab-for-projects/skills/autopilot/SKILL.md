---
name: autopilot
description: "Autonomous project coordination — assess the backlog, plan unplanned tasks, implement ready work, validate results, and document findings without checking in at each step."
argument-hint: "[project-name]"
mode: headless
agents:
  - manager
requires-mcp: tab-for-projects
---

# Autopilot

The user is opting out of the conversation loop. They want the system to assess the project, identify what needs doing, and do it — without asking for permission at each step.

## Protocol

1. **Resolve the project.** If the user passed an argument, match it against `list_projects`. Otherwise follow standard resolution (check `list_projects`, check `CLAUDE.md`, ask if ambiguous).

2. **Load project context.** Call `get_project` for the goal, requirements, and design.

3. **Gather knowledgebase context.** Call `list_documents` for the project. Collect all document IDs.

4. **Phase 1: Assessment.** Spawn the coordinator in coordinate mode (`subagent_type: "tab-for-projects:coordinator"`) with:
   - Project ID, goal, requirements, design
   - Scope: `"full"`
   - Mode: `"coordinate"`
   - All knowledgebase document IDs

   Run in the background. The coordinator will:
   - Assess backlog health and alignment with project goals
   - Do direct MCP work: fix task statuses, archive duplicates, create tasks for gaps it identifies
   - Return a structured assessment with **dispatch instructions**: which task IDs need planning, which need QA validation, which need documentation, and any focus areas for each

5. **Tell the user what's running.** Brief status: "Running autopilot — coordinator is assessing the project. I'll dispatch the team once it reports back."

6. **Phase 2: Dispatch.** When the coordinator completes, read its dispatch instructions and spawn agents in parallel:
   - **Planner** (`subagent_type: "tab-for-projects:planner"`) — for tasks the coordinator flagged as needing plans or decomposition. Pass the specific task IDs and any context the coordinator provided about what needs planning.
   - **QA** (`subagent_type: "tab-for-projects:qa"`) — for completed tasks the coordinator flagged as needing validation. Pass task IDs and any focus areas.
   - **Documenter** (`subagent_type: "tab-for-projects:documenter"`) — for completed work the coordinator flagged as needing knowledge capture. Pass task IDs and existing document IDs to avoid duplication.

   Only spawn agents that have work to do. If the coordinator found nothing for QA, don't spawn QA. All spawned agents run in the background, in parallel.

7. **Update the user.** Brief status on what was dispatched: "Coordinator found 8 tasks needing plans, 3 needing QA, and 2 worth documenting. Planner, QA, and documenter are running now."

8. **Phase 3: Implementation.** After Phase 2 agents complete, identify tasks ready for implementation and spawn implementer agents in dependency-ordered waves.

   **Identify implementable tasks.** Two sources:
   - The coordinator's `implement` dispatch array — task IDs the coordinator flagged as ready for implementation (have plans, acceptance criteria, status `todo`).
   - Newly-planned tasks — after the planner completes, call `list_tasks` to find tasks that now have `plan` and `acceptance_criteria` fields with status `todo`. The planner may have just created plans for tasks the coordinator flagged under `plan`.

   If the coordinator's dispatch has no `implement` key (coordinator predates this phase), fall back to `list_tasks` to find implementable tasks manually.

   If no implementable tasks exist from either source, skip this phase. Report "No tasks ready for implementation" in the final summary and proceed to step 10.

   **Group tasks into waves.** Read each task's plan, the coordinator's `implement` notes, and any dependency signals (e.g., "implement after [task ID] completes", references to other tasks' outputs). Tasks with no upstream dependencies go in wave 1. Tasks depending on wave 1 outputs go in wave 2, and so on. When dependency order is uncertain, default to sequential — correctness over speed.

   **Check for file conflicts within each wave.** Read the "Files to touch" sections of task plans. Tasks touching the same files within a wave must either be given to the same implementer agent or sequenced into sub-waves. Tasks touching disjoint files run in parallel.

   **Spawn implementer agents.** For each parallelizable unit within a wave, spawn `subagent_type: "tab-for-projects:implementer"` with `run_in_background: true` and `isolation: "worktree"`. Each implementer runs in its own git worktree on an isolated branch — this prevents parallel agents from stepping on each other's files. Pass:
   - Project ID
   - Task IDs for the unit
   - Project context (goal, requirements, design)
   - All knowledgebase document IDs

   Cap concurrent implementer agents at 3–5 per wave. If a wave has more parallelizable units than the cap, queue the overflow into sub-waves within the wave.

   Wait for all implementers in a wave to complete.

   **Merge step.** After all implementers in a wave finish, collect the branch names from their results. Spawn an ad-hoc merge agent (generic subagent, `run_in_background: true`) with a prompt to merge these branches into main sequentially and report any conflicts. Wait for the merge agent to complete before starting the next wave. If a merge fails, report the conflict in the progress update and skip any tasks in subsequent waves that depend on the failed task's output.

   **Progress updates between waves.** Tell the user: "Wave N complete: X tasks implemented, branches merged (task titles). Starting wave N+1: Y tasks." If any implementer reports failures, partial completions, or merge conflicts, report them before proceeding to the next wave.

9. **Phase 4: Post-implementation QA.** After all implementation waves complete, validate the newly implemented work.

   Collect task IDs that implementer agents completed (the implementer sets status to `done`). Tasks the implementer reported as incomplete or failed skip this phase — they appear in the final summary as needing attention.

   If there are completed tasks to validate, spawn QA (`subagent_type: "tab-for-projects:qa"`) with those task IDs. Run in the background.

   When QA completes, check results:
   - **Failures**: Report to the user in the final summary. Do NOT automatically re-implement or retry. The autopilot is autonomous but bounded — no retry loops.
   - **Passes**: Continue to results summary.

   If no tasks were implemented (Phase 3 was skipped or all implementations failed), skip this phase.

10. **Collect and present results.** As agents complete, collect their results. When all are done, present the full summary:
   - What the coordinator assessed and what direct actions it took (status fixes, new tasks, archives)
   - What the planner produced (plans, acceptance criteria, new tasks from decomposition)
   - What Phase 2 QA found on pre-existing completed work (pass/fail verdicts, qa-findings tasks created)
   - What the documenter captured (documents created or updated)
   - What was implemented — tasks completed, tasks that failed implementation, tasks skipped (with reasons)
   - What Phase 4 QA found on newly implemented work — pass/fail verdicts, qa-findings tasks created. Clearly separated from Phase 2 QA results.
   - What the coordinator chose NOT to act on and why
   - Items that need the user's judgment

## What Makes This a Skill

Autopilot is a **permission structure**. Without it, the manager asks before it acts — that's its nature as a thinking partner. Autopilot explicitly says: "I trust the system to make good calls. Go."

The multi-phase design makes the manager a team lead, not a delegator. Phase 1 sends the coordinator as an analyst — it reads the full project state, does what it can directly (status fixes, gap tasks, duplicate cleanup), and returns structured dispatch instructions for specialist work. Phase 2 has the manager spawn planner, QA, and documenter in parallel with the specific scoped work from the coordinator's findings. Phase 3 sends implementer agents to execute plans in dependency-ordered waves — each implementer runs in an isolated git worktree so parallel agents never conflict, with an ad-hoc merge step between waves to integrate branches back into main. Phase 4 runs QA on the freshly implemented work to catch issues before the user sees them. The coordinator doesn't need to hold the spawn button; the manager does that based on precise instructions about what needs doing and why.

The user should be able to type `/autopilot`, walk away, and come back to a project that's been triaged, planned, implemented, validated, and documented — with a clear summary of everything that happened.
