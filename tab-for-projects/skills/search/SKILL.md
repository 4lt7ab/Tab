---
name: search
description: Find documents and tasks in the Tab for Projects knowledgebase. Escalates through keyword, fuzzy title, tag, and folder filters until it finds the match — the user shouldn't need to retry with a different phrasing. Use when the user is looking for something they know (or suspect) exists but can't name exactly. Triggers on `/search` and phrases like "find that doc about X", "which task was about Y", "search the KB for Z".
argument-hint: "<query> [--scope=docs|tasks|all] [--project=<id or title>]"
---

A search skill that assumes the user is right — the thing they're looking for probably exists; the skill's job is to find it. Tries increasingly loose filters across titles, summaries, tags, folders, and task metadata before giving up. Reports what it tried so the user can refine instead of guessing.

## Trigger

**When to activate:**
- User invokes `/search <query>` optionally with `--scope` or `--project` flags.
- User says "find that doc about X", "which task was about Y", "search the KB for Z", "what was that convention on W".
- User is trying to locate something they recall existing but can't name precisely.

**When NOT to activate:**
- User wants to create — use `/fix`, `/plan-project`, or `/save-document`.
- User wants full project context — use `/get-project`.
- User wants code search in the current repo — use `Grep` or `Glob` directly.

## Requires

- **MCP:** `tab-for-projects` — for `list_documents`, `list_tasks`, `search_documents`, `get_document`, `get_task`.

## Behavior

### 1. Parse the query

Extract:

- **Scope** — `--scope=docs|tasks|all`. Default: `all`.
- **Project filter** — `--project=<id or title>`. If absent, search is cross-project.
- **Likely hints** embedded in the query:
  - A tag-ish word (`conventions`, `decision`, `architecture`, `guide`, etc.) — keep it handy for tag filtering.
  - A folder-ish word (`conventions`, `guides`, `decisions`, `patterns`) — keep for folder filtering.
  - A status/category word for tasks (`done`, `archived`, `bugfix`, `infra`) — keep for task filtering.
  - Core search terms — what remains after stripping the above.

### 2. Escalation ladder

Run the ladder top-down. Stop at the first rung that returns useful results (roughly: 1–15 hits). Do **not** stop at the first rung that returns *any* hits — a single weak hit on rung 1 isn't better than a clean five on rung 3.

**Docs scope:**

1. **Exact title match** — `list_documents` with `title: <core query>`.
2. **Search across title + summary** — `list_documents` with `search: <core query>`.
3. **Tag filter** — if query had a tag-ish hint, `list_documents` with `tag: <hint>`.
4. **Folder filter** — if query had a folder-ish hint, `list_documents` with `folder: <hint>`.
5. **Broad listing + client-side filter** — pull recent documents (limit 50) and filter by looser substring match on title/summary.

**Tasks scope:**

1. **Exact title match** — `list_tasks` with `title: <core query>`.
2. **Category filter** — if query had a category hint, `list_tasks` with `category: <hint>`.
3. **Group filter** — if query looked like a `group_key`, `list_tasks` with `group_key: <hint>`.
4. **Status filter** — if user said "done" / "archived" / etc., narrow by status.
5. **Broad listing + client-side filter** — pull recent tasks (limit 50) and filter.

**All scope:** run docs ladder and tasks ladder in parallel, merge results.

### 3. Present results

Show the top matches in a compact, scannable format. For each result, include enough signal for the user to pick the right one:

```
Docs (3):
  01KPCW… "Conventions: Project Inference" [conventions/reference] — how skills resolve the active project
  01KPAK… "Template: Skill Headers" [conventions/reference] — standard SKILL.md section template
  01KN8S… "Prompt Quality Conventions" [conventions/reference] — six rules for writing agent/skill prompts

Tasks (1):
  01KNK4… "Standardize skill frontmatter schema" (done, low/high, docs)

Searched: exact title, fuzzy title+summary. Refine with --scope or add a folder/tag hint if the match isn't here.
```

Always state **what was searched** at the bottom. The user might want to escalate further manually.

### 4. When the ladder returns nothing

Don't say "no results." Say what was tried and propose refinements:

```
Nothing matched "auth token rotation".
Tried: exact title, fuzzy title+summary, tag=security, folder=conventions.
Suggestions: try --scope=tasks, or broaden the query (drop "rotation"?).
```

## Output

A ranked list of doc and/or task hits with enough metadata to choose. No full document contents — that's `get_document`'s job. The skill is a finder, not a reader.

## Principles

- **The user's query is right.** The match probably exists. Loosening the filter is the skill's job, not the user's.
- **Recall over precision, with ceilings.** Better to return 10 plausible hits than 1 tight match; but don't dump 50.
- **Show your work.** State which filters ran. Lets the user refine intelligently.
- **Stop escalating when results are good enough.** A clean five on rung 2 beats noisy twenty on rung 5.

## Constraints

- **Read-only.** This skill never writes to the MCP.
- **No fabricated hits.** If the MCP returns nothing, say so. Don't guess IDs or titles.
- **No full-content dumps.** Show summaries, tags, folder — not the whole document body. The user asks for full content separately.
- **Cross-project by default unless `--project` is set.** Don't assume scope from cwd.
