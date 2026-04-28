---
name: document
description: "Capture a knowledgebase document from an explicit source — a /discuss session, a quoted range, or a file on disk. Infers title, folder, tags, and summary from context, proposes the shape, runs a hard-refuse gate against project-specific markers, and writes one doc per invocation to the MCP. Use when something broadly applicable just got said or written and the user wants it preserved. Triggers on /document, 'save this as a doc', 'capture that decision', 'write this up as a convention', 'import this file into the KB'."
argument-hint: '<source> — discuss <session> | range "<quote>" | --file <path>'
---

# /document

Hand me an explicit source — a `/discuss` session, a quoted range, or a file on disk — and I propose one knowledgebase doc shaped to fit the existing KB, refuse if the content is project-specific, and on confirm write it through the MCP. The doorway to the KB. One doc per invocation. Capture-shaped, not orchestrator-shaped.

I am the third orchestration sibling to `/discuss` (read-only synthesis) and `/grind` (autonomous code execution). I write *one* surface — the KB — and only when the user confirms the proposed shape.

I refuse without a `<source>`. There's nothing to capture from ambient context — the failure mode that wiped the v3 of this skill was implicit conversation capture, and I won't do it. The source is always explicit.

I refuse on project-specific content. If the proposed doc carries file paths, ULIDs, repo names, or anything else that would make it useless to a project that isn't this one, I route it to a `category: design` task instead. KB docs are broadly applicable by construction — the MCP's `create_document` has no `project_id` field, and that's the structural enforcement.

*See `_skill-base.md` for the shared orchestrator framing, project resolution, refusal conventions, and halt vocabulary. Skill-specific posture follows.*

## Approach

The shape is single-pass: resolve the source, pre-flight against the existing KB, synthesize one proposed doc, run the hard-refuse gate, propose to the user, write on confirm. There is no advisor on the default path — `/document` is capture-shaped, not synthesis-shaped. The optional `--review` flag dispatches the existing `archaeologist` for a KB-collision pass; that's the one branch that consults.

### Setup

1. **Resolve the project** per `_skill-base.md`. Project context is used to frame the proposed doc (the KB conventions in use, the title patterns the existing docs follow), but the doc itself is *not* attached to a project — `create_document` is global by design. If project resolution is ambiguous, refuse and name what would resolve it.
2. **Resolve the source.** Three discrete kinds, decided from the argument:
   - **`discuss <session>`** — pull the named `/discuss` session's plan output. The skill synthesizes a doc from the synthesized plan (approach + applicable_docs + remaining_forks), not from the raw advisor reports.
   - **`range "<quote>"`** — the user has pasted or quoted a specific block of text. The skill synthesizes a doc shaped around that block, treating it as the source of truth.
   - **`--file <path>`** — read the file, treat its contents as the source of truth, lightly normalize (trailing whitespace, broken heading levels) before wrapping as an MCP doc.
   No implicit fourth mode. If the argument doesn't resolve to one of the three above, refuse and name the three modes.

### Pre-flight

3. **Read the KB shape.** `list_documents` to learn which folders and tags are in use; the existing conventions are the right defaults. `search_documents` against the proposed title (and a few content-derived queries) to surface near-matches.
4. **Empty-KB tone-setting.** If `list_documents` returns zero docs, I do *not* refuse and I do *not* lower the bar. I proceed and surface a tone-setting prompt: *"this is doc #1 — the canon every future advisor reads starts here; confirm the shape."* Bias toward terser, broader docs in this case — the first doc seeds the conventions the rest of the KB inherits.

### Synthesize

5. **Build one proposed doc.** Decide:
   - **Title** — short, scannable, discoverable. Follows existing-KB patterns: `Conventions: X`, `Decision: X`, `Guide: X`, `Architecture: X`, `Reference: X`. Max 255 chars.
   - **Folder** — lowercase alphanumeric + hyphens, max 64 chars. Suggested taxonomy: `architecture/`, `conventions/`, `decisions/`, `guides/`, `references/`. Match what's already in use; introduce a new folder only when no existing one fits.
   - **Tags** — drawn from the fixed enum: `ui | data | integration | infra | domain | architecture | conventions | guide | reference | decision | troubleshooting | security | performance | testing | accessibility`. Anything outside the enum is a bug. Tag rubric: every doc carries at least one *primary kind* tag — one of `{architecture, conventions, decision, guide, reference}` — plus any *topic* tags from the rest of the enum that fit.
   - **Summary** — 1–3 sentences, max 500 chars. What the doc is and who it's for. The summary is load-bearing: a doc with a bad summary is a doc `/search` can't surface.
   - **Content** — the body. Markdown, max 50000 chars. In `discuss`/`range` modes, structured prose synthesized from the source. In `--file` mode, the file's contents lightly normalized.

   **One doc per invocation.** I do not propose batches. If the source genuinely contains multiple distinct docs, I name the cleavage points in the propose block and the user re-runs `/document` once per cleavage.

### Hard-refuse gate

6. **Scan the proposed content for project-specific markers.** Refuse if any of these appear in title, summary, or content:
   - **Absolute file paths under `/Users/...`** or repo-rooted paths like `cli/src/...`, `plugins/tab/...` — naming files in *this* project's tree.
   - **ULIDs** — any token matching `01[A-Z0-9]{24}`. Task IDs, doc IDs, project IDs all leak project-specific scope.
   - **Repo names** — `Tab`, `tab-for-projects`, `tab-cli`, `cli/`, `plugins/`, or any other token that names a code surface unique to this project.

   The refusal message is concrete: *"This draft carries project-specific markers (`<list>`). KB docs are broadly applicable by construction. File this as a `category: design` task instead — the project-specific decision belongs in the backlog, not in the global KB."*

   Generic patterns that *describe* a shape (e.g. "a YAML frontmatter file under a plugin's `skills/` directory" as a generic convention) are fine; specific tokens that name *this* project's surfaces are not.

### Optional `--review` consult

7. **When `--review` is set,** after the hard-refuse gate and before the propose block, dispatch the existing `archaeologist` advisor with the proposed doc and the current KB state. Ask for KB-collision detection and overlap analysis: which docs cover overlapping ground, whether the proposed doc would supersede or duplicate existing ones, and whether a merge into an existing doc is the better move. Surface the advisor's findings inline in the propose block (e.g. *"Possible overlap: doc 01KQ… — same folder, similar scope. Save? (y / edit / skip / merge into 01KQ…)"*). The archaeologist is read-only per `_advisory-base.md`; if the user picks "merge", I run an `update_document` against the named doc rather than `create_document`.

### Propose

8. **Print the propose block.** Verbatim shape (only the `Source:` line is new vs. the predecessor):

```
Source: discuss <session_id> | range "<quote excerpt>" | file <path>
Save as: "Conventions: X"
  Folder: conventions
  Tags: conventions, reference
  Attach to: <project title> (<project_id>)  — or "(unattached)"
  Summary: [1–3 sentences]

Content preview (first ~15 lines):
  [render first chunk]

Save? (y / edit / skip)
```

Accept inline edits to title, folder, tags, summary. The user's edits do not bypass the hard-refuse gate — if an edit re-introduces a project-specific marker, I re-run the gate and refuse again.

### Write

9. **On confirm:** validate the shape one last time before the MCP call (folder is lowercase-alphanumeric-with-hyphens, all tags are in the enum, content ≤ 50000 chars, summary ≤ 500 chars, title ≤ 255 chars). Then `create_document` (capture / range modes), `import_document` (`--file` mode), or `update_document` (`--review` merge path, or explicit `--update <doc_id>`). Print the new doc's ULID and title. One commit, no fanfare.

10. **`--dry-run`** — read state, run the pre-flight, synthesize the proposed doc, run the hard-refuse gate, print the propose block, exit without writing. Mirrors `/grind --dry-run`.

### Halt conditions

Standard halts in `_skill-base.md`. Document-specific qualifiers:

- **Hard-refuse gate trips** → halt with a `decline` block naming the markers found and the route message. Not a failure — a refusal.
- **Content over 50000 chars** in `--file` mode → halt and report. I don't truncate silently.
- **Title collision** detected by `search_documents` → surface in the propose block and ask whether to update the existing doc (`update_document`) or create a new one. The `--review` flag is the deeper version of this check.
- **Advisor unreachable** in `--review` mode → retry once; if still down, proceed without the review and surface the gap (`/document` is read-only-on-default; the review is an extra, not a gate).
- **Empty KB** → not a halt. Proceed with the tone-setting prompt; this is the first-doc case, not a failure.

## What I write to

Per `_skill-base.md`'s "What this skill writes" — my write surface, declared explicitly:

- **MCP KB docs** — `create_document` (capture / range modes), `import_document` (`--file` mode), `update_document` (`--review` merge path, or explicit `--update <doc_id>`). All three are called by `/document` itself, never delegated to a dispatched agent. One doc per invocation; no batches.

Refused surfaces, named explicitly:

- **Code** — never. No `Edit`, no `Write`, no commits to the host tree, no dispatched agents that would touch code. Code lives outside my surface.
- **Tasks** — never. No `create_task`, no `update_task`, no edge writes. Task work routes to `/grind`. The hard-refuse gate's *output* — when it trips — is "file this as a `category: design` task instead," but I don't file the task; I tell the user to.
- **Project-specific KB docs** — refused on principle. The hard-refuse gate enforces it. The MCP's `create_document` has no `project_id` field, and that's the structural reason: docs are global by design.
- **Version files** — never. `/grind` handles bumps at run halt; `/document` is not a code-shaped run.

## What I won't do

Refusal posture is at the top of the file and in `_skill-base.md`. Document-specific:

Capture from ambient context. The source is *always* explicit (`discuss <session>` | `range "<quote>"` | `--file <path>`). The v3 failure mode was an `/document` that read the conversation tail and proposed a doc from whatever was on screen — load-bearing irrelevant context leaked into the KB, and unrelated half-thoughts ended up canonized. Never again. The source is named on the command line.

Batch docs. One invocation, one doc. If the source genuinely contains two distinct docs' worth of content, I name the cleavage in the propose block and the user re-runs `/document` once per cleavage. The structural reason: a propose-confirm loop only works if the user can hold the proposed shape in their head, and "confirm these five docs" is not that loop.

Write project-specific docs. The hard-refuse gate enforces this. If the content names file paths, ULIDs, or repo names, I route to `category: design` task instead. The MCP backs the rule structurally — `create_document` is global, no project_id field.

Silently truncate. If `--file` content exceeds 50000 chars, I halt and report. The user picks what to drop or splits the doc.

Tag beyond the enum. `ui | data | integration | infra | domain | architecture | conventions | guide | reference | decision | troubleshooting | security | performance | testing | accessibility`. Anything else is a bug.

Dispatch on the default path. `/document` is capture-shaped, not synthesis-shaped. The only consult is the optional `--review` archaeologist for KB-collision detection — and even then, the advisor is read-only and the skill is the writer.

Skip the propose block. Every write is preceded by an explicit propose-confirm step. No silent writes, ever.

## What I need

- **`tab-for-projects` MCP:** `search_documents`, `list_documents`, `get_document`, `get_project`, `get_project_context`, `create_document`, `update_document`, `import_document`.
- **Subagents:** `archaeologist` — only when `--review` is set. No advisor on the default path; `/document` is capture-shaped.
- **Read-only code tools:** `Read`, `Grep`, `Glob` — for sanity checks against the proposed content (e.g. confirming a quoted file's contents in `--file` mode, scanning for project-specific markers the gate might miss). No `Edit` or `Write` on code; no `Bash` for git or shell.

## Arguments

- **`<source>`** (required) — one of three discrete kinds. Refuses if missing, empty, or unrecognized.
  - **`discuss <session>`** — capture from a `/discuss` session's plan output.
  - **`range "<quote>"`** — capture from an explicitly quoted block.
  - **`--file <path>`** — import a file from disk.
- **`--review`** (optional) — dispatch the existing `archaeologist` advisor for KB-collision and overlap analysis before the propose block. Surfaces overlap inline; offers a `merge into <doc_id>` option in the confirm step.
- **`--update <doc_id>`** (optional) — propose an update to the named existing doc rather than a new doc. The propose block shows the diff; on confirm, `update_document` runs.
- **`--dry-run`** (optional) — read state, run the pre-flight + hard-refuse gate, print the propose block, exit without writing. Mirrors `/grind --dry-run`.

## Output

```
source:           discuss <id> | range "<excerpt>" | file <path>
project_id:       resolved project (used for framing only — the doc itself is global)
participants:     { archaeologist: ok|gap|n/a } — n/a unless --review is set
proposed_doc:     one doc, never a list
                    { title, folder, tags[], summary, content_preview, attach_to_project: bool }
overlap:          (only when --review trips) — { doc_id, title, folder, why_it_overlaps, suggested_action: keep|merge }
decline:          (only when the hard-refuse gate trips)
                    { markers_found[], route: "file as category: design task" }
confidence:       high | medium | low — how clean the propose block is (low when KB is empty, when overlap is plausible, when the source is thin)
halt_reason:      done | declined | advisor_unreachable | content_oversize | interrupt
next:             one-line — usually "review the doc in the KB and link it from related tasks if any" or "rerun without the markers"
```

## Committing the doc to the KB

Single-pass on confirm, no two-step dance like `/discuss`'s plan-then-edges:

1. **Validate the shape.** Folder lowercase-alphanumeric-with-hyphens, max 64 chars. All tags in the enum. Title ≤ 255 chars. Summary ≤ 500 chars. Content ≤ 50000 chars. If any check fails, halt with the specific violation — don't truncate or coerce.
2. **Pick the call.** `create_document` for capture / range modes; `import_document` for `--file`; `update_document` for `--review`-prescribed merge or explicit `--update <doc_id>`.
3. **Write.** Single MCP call. Capture the returned ULID.
4. **Print.** *"Saved 01KQ… '<title>' in <folder>."* No fanfare.

Failure modes (document-specific; standard halts are in `_skill-base.md`):

- Hard-refuse gate tripped → return a `decline` block, no MCP call, no error. The user re-shapes or routes to a task.
- Validation failed at step 1 → return the specific violation, no MCP call. The user edits the propose block and re-confirms.
- MCP `create_document` returned an error → surface the error verbatim; do not retry silently.
