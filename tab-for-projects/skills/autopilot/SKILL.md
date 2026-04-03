---
name: autopilot
description: "Autonomous project coordination — assess the backlog, plan unplanned tasks, validate completed work, and document findings without checking in at each step."
argument-hint: "[project-name]"
---

# Autopilot

The user is opting out of the conversation loop. They want the system to assess the project, identify what needs doing, and do it — without asking for permission at each step.

## Protocol

1. **Resolve the project.** If the user passed an argument, match it against `list_projects`. Otherwise follow standard resolution (check `list_projects`, check `CLAUDE.md`, ask if ambiguous).

2. **Load project context.** Call `get_project` for the goal, requirements, and design.

3. **Gather knowledgebase context.** Call `list_documents` for the project. Collect all document IDs — the coordinator will need them to make informed decisions.

4. **Spawn the coordinator in coordinate mode.** Use `subagent_type: "tab-for-projects:coordinator"` with:
   - The project ID, goal, requirements, and design
   - Scope: `"full"`
   - Mode: `"coordinate"`
   - All knowledgebase document IDs

   Run in the background. The coordinator will autonomously:
   - Assess backlog health and alignment with project goals
   - Spawn the planner for tasks that need decomposition or plans
   - Spawn QA for completed tasks that need validation
   - Spawn the documenter for completed work that should be captured
   - Create tasks for gaps it identifies
   - Chain dependent work sequentially, parallelize independent work

5. **Tell the user what's running.** One line: "Running a full project sweep — planning, QA, and documentation as needed. I'll summarize when it's done."

6. **When the coordinator completes**, present the results:
   - What was assessed (scope, key findings)
   - What agents were spawned and what they produced
   - Tasks created, updated, or failed QA
   - Documents created or updated
   - What the coordinator chose NOT to act on and why
   - Any items that need the user's judgment

## What Makes This a Skill

Autopilot is a **permission structure**. Without it, the manager asks before it acts — that's its nature as a thinking partner. Autopilot explicitly says: "I trust the system to make good calls. Go." The coordinator's coordinate mode exists for exactly this purpose; the skill is the front door that grants it full autonomy for a single sweep.

The user should be able to type `/autopilot`, walk away, and come back to a project that's been triaged, planned, validated, and documented — with a clear summary of everything that happened.
