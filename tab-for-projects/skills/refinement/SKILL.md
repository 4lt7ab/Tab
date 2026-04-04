---
name: refinement
description: "Backlog refinement ceremony — structured walkthrough of active tasks with the user to ensure they're understood, scoped, and actionable before implementation."
argument-hint: "[project-name]"
mode: conversational
agents:
  - manager
requires-mcp: tab-for-projects
---

# Backlog Refinement

A structured ceremony for reviewing and improving the backlog collaboratively. The coordinator assesses; you and the user decide.

## Protocol

### Phase 1: Orient

1. **Resolve the project.** If the user provided an argument, match it against `list_projects`. Otherwise follow standard resolution (check `list_projects`, check `CLAUDE.md`, ask if ambiguous).

2. **Load project context.** Call `get_project` to pull the goal, requirements, and design.

3. **Spawn the coordinator for assessment.** Use `subagent_type: "tab-for-projects:coordinator"` with:
   - The project ID and context
   - Scope: `"full"`
   - Mode: `"report"`
   
   Run in the background. While waiting, call `list_tasks` filtering for `status: "todo"` and `status: "in_progress"` to get the active backlog.

4. **Present the session overview.** When the coordinator returns, combine its assessment with the task list. Show the user:
   - Project name and goal (one line)
   - The coordinator's health summary and key findings
   - A scannable task list: title, effort, impact, category, whether it has a plan
   - Tasks the coordinator flagged as underspecified, stale, or misaligned

Ask the user how they want to proceed — walk through everything, focus on flagged tasks, or start with a specific group.

### Phase 2: Refine

For each task the user wants to refine, follow this loop:

**Present.** Call `get_task` for full details. Show: title, description, effort/impact, plan (if any), acceptance criteria (if any), and what's missing or unclear.

**Discuss.** Work through the task with the user:
- Does the description capture *why* this task exists? Sharpen it together.
- Is this one task or three? Too granular or too broad?
- If unknowns exist, spawn a **background agent** to research the codebase while you keep talking.
- If effort is missing or feels wrong, discuss it.
- If the user has opinions about what "done" looks like, capture acceptance criteria.

**Persist.** After discussion, call `update_task` immediately with everything that was clarified — refined description, updated effort/impact, acceptance criteria. Don't batch updates for the end of the session. If the session is interrupted, every decision already made should be saved.

**Gate.** Before moving to the next task, confirm with the user: "Good on this one? Next?" This is the phase gate — the user explicitly closes each task's refinement.

### Phase 3: Close

When the user is done or the backlog is fully refined:

1. **Summarize.** How many tasks were refined, what was added, what estimates changed.
2. **Flag what's still open.** Tasks that need research (agents still running), tasks the user deferred, tasks that are still underspecified.
3. **Offer follow-up.** If tasks need plans, offer to spawn the planner (`subagent_type: "tab-for-projects:planner"`). If the user wants a coverage check, offer to spawn QA (`subagent_type: "tab-for-projects:qa"`).

Don't force a neat ending. If the user says "that's enough for now," that's enough.

## What Makes This a Ceremony

Refinement is not an assessment — the coordinator handles that. Refinement is a **decision-making session** where the user and the manager negotiate scope, priority, and clarity together. The coordinator's report seeds the conversation; the user's judgment shapes the backlog. Every task gets explicit attention and explicit closure before moving on.
