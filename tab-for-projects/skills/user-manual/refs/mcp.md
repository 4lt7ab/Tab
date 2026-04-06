# Tab for Projects MCP Reference

## Data Model

Three layers: **projects**, **tasks**, and **documents**.

```
Project
├── title          (required, max 255 chars)
├── goal           (why this project exists)
├── requirements   (what it must do)
├── design         (how it should work)
└── documents[]    (linked via attach/detach — many-to-many)

Task (belongs to a project)
├── title               (required, max 255 chars)
├── description          (context for future readers — the most valuable field)
├── plan                 (how to approach the work)
├── implementation       (what was actually done — filled after, not before)
├── acceptance_criteria  (what "done" looks like)
├── status               todo | in_progress | done | archived
├── effort               trivial | low | medium | high | extreme
├── impact               trivial | low | medium | high | extreme
├── category             feature | bugfix | refactor | test | perf | infra | docs | security | design | chore
├── group_key            (flat grouping label, max 32 chars)
└── dependencies[]       (edges: blocks | relates_to)

Document (standalone, linked to projects)
├── title       (required, max 255 chars)
├── summary     (max 500 chars — shown in list views)
├── content     (markdown, max 50k chars)
├── tags[]      (from a fixed set — see below)
└── favorite    (boolean — marks high-value references)
```

### Document Tags

Tags come from three categories. A document can have up to 20.

| Category | Values |
|----------|--------|
| Domain | `ui`, `data`, `integration`, `infra`, `domain` |
| Content Type | `architecture`, `conventions`, `guide`, `reference`, `decision`, `troubleshooting` |
| Concern | `security`, `performance`, `testing`, `accessibility` |

---

## Tools

### Projects

**`list_projects`** — Scan what exists. Start here to find a project ID.

```
{ title?: string, limit?: int, offset?: int }
```

Returns `{ data: [{ id, title, has_goal, has_requirements, has_design, created_at, updated_at }], total }`.

**`create_project`** — Start new work. Batch-create by passing multiple items.

```
{ items: [{ title: string, goal?: string, requirements?: string, design?: string }] }
```

**`get_project`** — Drill into one project. Returns all fields plus linked document summaries.

```
{ id: string }
```

**`update_project`** — Change project details or link documents. Only provided fields change.

```
{ items: [{ id: string, title?: string, goal?: string, requirements?: string, design?: string,
            attach_documents?: string[], detach_documents?: string[] }] }
```

**`delete_project`** — Permanent removal. **Cascades to all tasks in the project.** Cannot be undone.

```
{ ids: string[] }
```

### Tasks

**`list_tasks`** — Browse work. Returns summaries for scanning.

```
{ project_id?: string, status?: string[], effort?: string, impact?: string,
  category?: string, group_key?: string, blocked?: boolean, limit?: int, offset?: int }
```

- `status` is an **array**: `["todo", "in_progress"]`, not a single string.
- `effort`, `impact`, `category` are single enum strings.
- `blocked`: `true` = waiting on dependencies, `false` = ready to work on.

Returns `{ data: [{ id, title, status, effort, impact, category, group_key, is_blocked, created_at, updated_at }], total }`.

**`create_task`** — Add work items. Status defaults to `todo`.

```
{ items: [{ project_id: string, title: string, description?: string, plan?: string,
            implementation?: string, acceptance_criteria?: string, status?: string,
            effort?: string, impact?: string, category?: string, group_key?: string }] }
```

**`get_task`** — Read full task detail (description, plan, implementation, acceptance criteria, dependencies).

```
{ id: string }
```

**`update_task`** — Change task fields or manage dependencies. Only provided fields change.

```
{ items: [{ id: string, title?: string, description?: string, plan?: string,
            implementation?: string, acceptance_criteria?: string, status?: string,
            effort?: string, impact?: string, category?: string, group_key?: string,
            add_dependencies?: [{ task_id: string, type: "blocks" | "relates_to" }],
            remove_dependencies?: [{ task_id: string }] }] }
```

The specified `task_id` becomes the blocker/relation — the task being updated is the target.

**`delete_task`** — Permanent removal. Cannot be undone.

```
{ ids: string[] }
```

**`get_ready_tasks`** — **Find actionable work.** Returns unblocked tasks. Defaults to `todo`.

```
{ project_id: string, status?: string[] }
```

`project_id` is **required**. Pass `status` array to check other statuses (e.g. `["in_progress"]`). When no tasks are ready but matching tasks exist, returns diagnostics (counts, blocked info).

**`get_dependency_graph`** — Understand task ordering for a project.

```
{ project_id: string, status?: string[] }
```

`project_id` is **required**. Returns all dependency edges and task metadata. `blocked_task_ids` is always computed from the full graph regardless of status filter.

### Documents

**`list_documents`** — Browse the knowledgebase. Returns summaries.

```
{ tag?: string, title?: string, search?: string, project_id?: string,
  favorite?: boolean, limit?: int, offset?: int }
```

- `search` searches title and summary text.
- `project_id` finds docs linked to that project.

Returns `{ data: [{ id, title, summary, has_content, favorite, tags, created_at, updated_at }], total }`.

**`create_document`** — Capture knowledge. Documents are standalone — link to projects separately via `update_project`.

```
{ items: [{ title: string, summary?: string, content?: string, tags?: string[],
            favorite?: boolean }] }
```

**`get_document`** — Read full document content. **Content can be large** (up to 50k chars) — only fetch when you need actual content, not just metadata.

```
{ id: string }
```

**`update_document`** — Modify documents. Only provided fields change, **except tags — providing tags replaces all existing tags.**

```
{ items: [{ id: string, title?: string, summary?: string, content?: string,
            tags?: string[], favorite?: boolean }] }
```

**`delete_document`** — Permanent removal. Removes tags and project associations. Cannot be undone.

```
{ ids: string[] }
```

---

## Patterns

**List then get.** All three layers follow the same pattern: `list_*` returns lightweight summaries for scanning, `get_*` returns the full record. Use list to find IDs, get to drill in.

**Batch operations.** All `create_*` and `update_*` tools accept `items[]` arrays. Use batch calls when working with multiple records.

**Documents are independent.** They don't belong to a project — they're linked via `update_project` with `attach_documents` / `detach_documents`. One document can link to many projects.

**Dependencies flow one direction.** When you call `update_task` with `add_dependencies: [{task_id: "X", type: "blocks"}]`, task X becomes the blocker and the task you're updating becomes blocked. A blocked task won't appear in `get_ready_tasks` until its blockers are `done` or `archived`.

**Favorites mark high-value docs.** Use `list_documents` with `favorite: true` to find reference documents worth attaching to new projects.

**Status filtering defaults matter.** `get_ready_tasks` defaults to `todo`. `list_tasks` returns all statuses unless you filter — for active work, pass `status: ["todo", "in_progress"]`.
