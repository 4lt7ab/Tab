---
name: retro
description: "Scan the current conversation for implicit work items, synthesize them into structured tasks, and batch-create them after user review."
argument-hint: "[project ID or name]"
---

# Retro

Extract undone work from conversation into tasks.

## Trigger

**When to activate:**
- User invokes `/retro`
- User says "let's retro," "what work came out of this," "capture the work"
- End of a session where decisions were made but no tasks were created

**When NOT to activate:**
- Breaking down a single task into subtasks — that's the planner agent
- Creating one specific, already-known task — call `create_task` directly
- Reviewing or triaging existing tasks — use `list_tasks` / `get_ready_tasks`

## Requires

- **MCP:** tab-for-projects (`create_task`, `list_projects`)
- **Context:** A conversation with enough substance to extract work from. If thin, say so and stop.

## Workflow

### 1. Identify the project

Use the project ID or name if provided. If the conversation makes it obvious, use that. Otherwise ask — list projects via `list_projects`.

Do not guess. A task in the wrong project is worse than no task.

### 2. Scan for work signals

Read the conversation and extract anything that implies undone work:

| Signal | Examples |
|--------|----------|
| Decisions not yet acted on | "We should," "Let's go with" |
| Bugs found | Error traces, workarounds applied |
| Features discussed | Capabilities mentioned, designs sketched |
| Refactoring identified | Tech debt acknowledged |
| Explicit follow-ups | "TODO," "we'll need to," "next step" |
| Gaps | Missing tests, outdated docs |

Ignore work already completed in the conversation.

### 3. Synthesize candidate tasks

For each item, produce:

```
Title:               {imperative — "Add validation to signup form"}
Summary:             {1-2 sentences — what and why}
Category:            {feature | bugfix | refactor | test | perf | infra | docs | security | design | chore}
Effort:              {trivial | low | medium | high | extreme}
Acceptance criteria: {testable conditions for "done"}
Group:               {shared key for related tasks, if any}
```

Tasks sized `extreme` should be flagged for decomposition rather than created as-is.

Related tasks share a `group_key` — short, descriptive (e.g., `auth-rework`, `api-validation`).

### 4. Present for review

Show all candidates in a numbered list with full fields. Ask the user to keep, edit, drop, or add. Do not create tasks until the user confirms.

### 5. Create tasks

Batch-create approved tasks:

```
create_task({
  items: [
    {
      project_id: "...",
      title: "...",
      summary: "...",
      category: "...",
      effort: "...",
      acceptance_criteria: "...",
      group_key: "..."
    }
  ]
})
```

### 6. Report

Summarize: task count, project name, table of titles with category and effort. Note group membership. Report failures separately.
