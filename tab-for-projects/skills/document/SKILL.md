---
name: document
description: Capture a knowledgebase document from the current conversation or an existing file. Infers doc type (decision, convention, guide, reference), folder, tags, and summary from context, proposes the shape, and writes to the MCP. Optionally attaches the document to a project. Use when something worth preserving just got said, decided, or written. Triggers on `/document` and phrases like "save this as a doc", "capture that decision", "write this up as a convention", "import this file into the KB".
argument-hint: "[optional: file path to import, or one-line title hint]"
---

The "this deserves to be a doc" skill. The user just worked through something — a decision, a pattern, a convention, a how-to — and wants it captured without opening the doc app, picking a folder, or tagging by hand. The skill reads the conversation (or a pointed-at file), proposes title / summary / folder / tags / content shaped to the existing KB, confirms once, and writes.

## Trigger

**When to activate:**
- User invokes `/document` with or without a file-path argument.
- User says "save this as a doc", "capture that decision", "write this up as a convention", "import this file into the KB", "file this under guides".
- A decision or convention just crystallized in conversation and the user wants it preserved.

**When NOT to activate:**
- User wants to create a task — use `/fix` or `/project`.
- User wants to search an existing doc — use `/search`.
- Content isn't ready — offer to keep discussing rather than saving a half-formed doc.

## Requires

- **MCP:** `tab-for-projects` — for `create_document`, `import_document`, `list_documents`, `update_project` (when attaching).

## Behavior

### 1. Pick a mode

Two modes, decided from the invocation:

- **Capture mode** — no file argument, or argument is a short title hint. The skill synthesizes content from the recent conversation.
- **Import mode** — the argument is a file path that exists. The skill reads the file and wraps it as an MCP document.

### 2. Resolve the project (only when attaching)

Documents can exist unattached. Default behavior is to propose attachment only when the content is clearly project-specific. To decide the target project:

1. Explicit `--project=<id or title>` argument wins.
2. Read `.tab-project` at repo root if present.
3. Parse git remote `origin`; exact repo-name match is high confidence.
4. Match cwd basename and parent segments against project titles.
5. Fall back to most recently updated plausible project. Never sole signal.

If confidence is below **confident** and content looks project-specific, ask. If content looks generic (see step 3), skip attachment entirely.

### 3. Classify the document

Decide doc type from content and conversation signals. Each type implies a default folder and tag set:

- **Decision** — "we decided", "we're going with", a pro/con thread that resolved. Folder: `decisions`. Tag: `decision` (+ domain tag if obvious).
- **Convention** — a rule, pattern, or standard the user wants to apply consistently. Folder: `conventions`. Tags: `conventions`, `reference`.
- **Guide** — a how-to, walkthrough, or tutorial-style write-up. Folder: `guides`. Tag: `guide`.
- **Reference** — a specification, schema dump, table of facts, or anything lookup-shaped. Folder: `reference` or topic-specific (`patterns`, `architecture`). Tag: `reference`.
- **Note** — a quick capture that doesn't fit the above. No folder (or `notes`). No specific tag.

Generic rule for folder/tag choice: **match what's already there**. Before proposing a folder or tag, list existing documents (`list_documents`) to see conventions in use. Introduce new folders or tags sparingly and only when no existing one fits.

### 4. Build the document

Synthesize:

- **Title** — short, scannable, discoverable. Follows patterns in the existing KB: `Conventions: X`, `Decision: X`, `Guide: X`, `Template: X`, `Architecture: X`. Prefer the pattern that matches the type.
- **Summary** — 1–3 sentences, max 500 chars. What the doc is and who it's for. Enough signal that `/search` can surface it correctly.
- **Content** — the body. In capture mode, structured markdown synthesized from conversation. In import mode, the file's contents, lightly normalized (trailing whitespace, heading levels if obviously broken).
- **Folder** — lowercase alphanumeric + hyphens, max 64 chars. From step 3.
- **Tags** — 0 or more from the MCP's enum. From step 3.

### 5. Propose, then write

Show the proposed document before writing:

```
Save as: "Conventions: X"
  Folder: conventions
  Tags: conventions, reference
  Attach to: Tab (01KN6H…)
  Summary: [1–3 sentences]

Content preview (first ~15 lines):
  [render first chunk]

Save? (y / edit / skip attachment)
```

Accept edits inline (title, folder, tags, summary). Once confirmed, call `create_document` (capture mode) or `import_document` (import mode). If attachment was approved, follow with `update_project` adding the document as a `reference` link (or whatever type matches — `decision` for decisions, etc.).

### 6. Close

Report the new document's ULID and title. No fanfare.

```
Saved 01KQ… "Conventions: X" in conventions folder, attached to Tab.
```

## Output

A document in the MCP, optionally linked to a project. The document starts discoverable: correct folder, correct tags, a summary that `/search` can match on. Skill closes with a one-line confirmation.

## Principles

- **Match the KB, don't reinvent it.** Existing folders, tags, and title patterns are the right defaults. Novel conventions get introduced rarely and deliberately.
- **The summary is load-bearing.** A doc with a bad summary is a doc `/search` can't find. Write the summary like the user will only ever see it in search results.
- **Capture, don't polish.** A saved decision is more valuable than a perfect one still in a thread. Accept "good enough to be findable."
- **Attachment is a choice.** Generic conventions live unattached and apply everywhere. Project-specific notes live attached. Don't over-attach.

## Constraints

- **No writes below confident project inference** when attaching. Ask or skip the attachment.
- **No silent writes.** Every document is proposed before it's created.
- **Don't overwrite existing documents by accident.** If a title collision shows up in `list_documents`, surface it and ask whether to update the existing doc (via `update_document`) or create a new one.
- **Content length cap.** `create_document` accepts up to 50,000 chars. If import-mode content exceeds this, stop and report — don't truncate silently.
- **Don't tag beyond the MCP enum.** The enum is: `ui`, `data`, `integration`, `infra`, `domain`, `architecture`, `conventions`, `guide`, `reference`, `decision`, `troubleshooting`, `security`, `performance`, `testing`, `accessibility`. Anything else is a bug.
