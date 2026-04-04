---
name: plan
description: "Turn work descriptions into structured tasks with implementation plans and acceptance criteria."
argument-hint: "[project-id task-ids... or work-description]"
inputs: "project-id (required), task-ids[] (optional — plan these existing tasks), work-description (optional — decompose into new tasks)"
mode: headless
agents:
  - planner
requires-mcp: tab-for-projects
---

# Plan

## Research the Codebase

This is the most important step. Do not plan blind.

For the work you're decomposing (or for each existing task you're planning):

- **Where the change lives.** Find the files, modules, and layers that are relevant. Don't guess — search. Use glob patterns, grep for symbols, read the actual code.
- **How it works today.** Understand the current behavior, data flow, and architecture in the area you'll be changing. Read enough code to have a real mental model.
- **What touches it.** Find callers, consumers, tests, configs, and anything else that would be affected by the change.
- **What patterns exist.** Look at how similar things were done elsewhere in the codebase. Plans should follow established conventions, not invent new ones.
- **What could go wrong.** Identify edge cases, breaking changes, migration concerns, or tricky interactions.

Spend the time here. A plan built on shallow understanding is worse than no plan — it creates false confidence. Read the code. Understand the code. Then plan.

## Decompose the Work

*Skip this if you were given specific task IDs to plan — those tasks already exist.*

Break the work into tasks that are:

- **Action-oriented** — titles start with a verb. "Define API schema" not "API schema."
- **Right-sized** — small enough to be completable in a focused session, large enough to be meaningful. If a task needs sub-tasks, it's probably a group, not a task.
- **Independent where possible** — minimize dependencies between tasks. When dependencies exist, note them in the description.
- **Honestly estimated** — use the effort scale based on actual complexity, not optimism.

For each task, determine:

| Field | What to write |
|-------|--------------|
| **title** | Short, scannable, action-oriented |
| **description** | Why this task exists, what context someone needs, what decisions led here. Write for someone reading next week with zero context. |
| **plan** | The implementation plan (see next section) |
| **acceptance_criteria** | What "done" looks like (see below) |
| **effort** | trivial / low / medium / high / extreme |
| **impact** | trivial / low / medium / high / extreme |
| **category** | feature / bugfix / refactor / test / perf / infra / docs / security / design / chore |
| **group_key** | A grouping label if tasks cluster naturally (max 32 chars) |

## Write Implementation Plans

For each task — whether newly created or pre-existing — write a plan that answers: **"If someone sat down to implement this right now, what would they need to know and do?"**

A good plan includes:

- **Approach** — the high-level strategy. What's being changed and why this approach over alternatives.
- **Files to touch** — specific file paths, not vague module names. Include what changes in each.
- **Sequence** — what order to make the changes in. What needs to happen first.
- **Patterns to follow** — reference existing code that demonstrates the conventions to use. Point to specific files or functions.
- **Edge cases and risks** — anything the implementer should watch out for.
- **Testing** — what needs to be tested and how. Reference existing test patterns if they exist.

A good plan does NOT include full implementation code — the implementer writes the code. However, showing a function signature, interface definition, config shape, or structural example is appropriate when it clarifies the contract the implementation must satisfy. A good plan also does NOT include vague hand-waving ("update the relevant files"), scope creep (plan what the task asks for, not what you think it should ask for), or the task description restated as a plan.

## Write Acceptance Criteria

For each task, write acceptance criteria that define what "done" looks like. These are the contract — QA will validate against them.

Good acceptance criteria are:

- **Specific** — "API returns 404 with error body when resource doesn't exist" not "handles errors properly"
- **Testable** — each criterion can be verified with a concrete action and expected outcome
- **Complete** — cover the happy path, error cases, and edge cases relevant to the task
- **Scoped** — only criteria for what this task delivers, not aspirational standards

Write them as a list of concrete, checkable statements. If you can't verify it, it's not a criterion — it's a wish.

## Persist to MCP

**For new tasks** (decomposition): call `mcp__tab-for-projects__create_task` with all fields populated. Batch all creates into a single call when possible.

```
items: [{
  project_id: "<project_id>",
  title: "<title>",
  description: "<description>",
  plan: "<plan>",
  acceptance_criteria: "<acceptance_criteria>",
  effort: "<effort>",
  impact: "<impact>",
  category: "<category>",
  group_key: "<group_key>"
}]
```

**For existing tasks** (planning only): call `mcp__tab-for-projects__update_task` to write the plan and acceptance criteria. Batch all updates into a single call when possible. Only update `plan` and `acceptance_criteria` — don't change other fields on existing tasks unless the prompt explicitly asks you to.

```
items: [{
  id: "<task_id>",
  project_id: "<project_id>",
  plan: "<plan>",
  acceptance_criteria: "<acceptance_criteria>"
}]
```
