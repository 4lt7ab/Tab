---
name: ship
description: "Pre-push sweep that caps a version. Bumps the code version, reviews README/CLAUDE.md drift, dispatches `archaeologist` to synthesize north-star (`favorite: true`) doc edits against the in-progress group's version brief, deletes the brief, and applies KB writes + code edits in a single commit. Does not push. Use when the version's work is committed and the branch is ready to go out."
argument-hint: "[--patch | --minor | --major] [--dry-run]"
---

A pre-push checkpoint that caps a version. `/ship` reads the commits since the last version tag, surfaces stale README/CLAUDE.md against the diff, looks up the version brief for the in-progress group, dispatches `archaeologist` to synthesize edits to the project's north-star (favorited) docs against that brief, and — on user confirmation — applies the version bump, the doc updates, and the brief deletion in a single commit. It never pushes. The user ships.

The shape: existing scan/sweep stays; north-star synthesis is the new pass; brief deletion is non-optional on apply because the brief is 1:1 with the version and git history is the historical record.

## Trigger

**When to activate:**
- User invokes `/ship`, optionally with a bump hint (`--patch`, `--minor`, `--major`).
- User says "cut a version", "get this ready to push", "run the ship sweep", "prep for release".
- A version's work just landed via `/develop` + `/qa` and the user wants to package it.

**When NOT to activate:**
- No commits since the last version tag — there's nothing to ship. Say so and stop.
- User is mid-work and hasn't committed — the sweep needs commits to read. Point them back to `/develop` or direct commits.
- User wants to push — this skill stops at the commit. Pushing is the user's call.

## Behavior

The skill flows in five phases: **Scan** (commit range), **Sweep** (stale README / CLAUDE.md), **Synthesize** (archaeologist on north-star docs against the version brief), **Confirm** (one approval gate), **Apply** (write the bump + doc updates + brief deletion in a single commit).

### 1. Scan — determine the commit range and the in-progress group

1. Find the last version tag. Priority: nearest tag on current branch matching a semver-ish pattern (`v1.2.3`, `1.2.3`, or plugin-prefixed like `tab-for-projects-2.3.0`). Fall back to initial commit if no tag exists.
2. Read commits since the tag with `git log <tag>..HEAD --oneline --no-merges`.
3. If the range is empty, say so and stop. Nothing to ship.
4. Read the full diff with `git diff <tag>..HEAD --stat` to get the file list for the doc sweep.
5. Resolve the project via the standard inference (`.tab-project` → git remote → cwd → recent activity), pull `get_project_context`, and identify the **in-progress group** — the version slug whose tasks have just landed. The version brief lives under that group.
6. Infer a version bump from commit types:
   - `breaking:` or `!:` in any subject → **major**
   - `feat:` / `add:` present → **minor**
   - `fix:` / `chore:` / `refactor:` / anything else → **patch**
   - A CLI flag (`--patch`, `--minor`, `--major`) overrides the inference.

### 2. Sweep — surface stale README and CLAUDE.md

From the diff's file list, identify docs that plausibly need updating:

- **README.md** (at any depth) is stale if: user-facing features were added/removed, CLI invocations changed, installation steps changed, or the file is named in the diff. Scan commit subjects for these signals.
- **CLAUDE.md** (at any depth) is stale if: a new module was added, an agent/skill was added or renamed, conventions changed, or the structure-tree portion doesn't match the filesystem.

For each doc the sweep flags, Read it and propose a targeted edit — not a rewrite. The user confirms, edits, or skips per-doc at the confirm gate.

If no docs look stale, the sweep returns "no README / CLAUDE.md drift detected." That's allowed.

### 3. Synthesize — archaeologist on north-star docs against the brief

1. **Read the version brief.** Look up the brief for the in-progress group via `search_documents` against the group slug (or whatever folder convention the project uses). The brief is one doc, 1:1 with the version. If no brief exists, note that in the report and skip the synthesis dispatch — there's nothing to synthesize against.
2. **Pull the favorited docs.** `list_documents` with `favorite: true` scoped to the project. These are the north-star docs — the ones the project marked as load-bearing for its long-running shape (architecture overviews, conventions, top-level guides).
3. **Dispatch `archaeologist` in north-star synthesis mode.** Inputs: the version brief (full content) and the favorited doc set (IDs and content). The dispatch asks for proposed edits per favorited doc — what the brief says the version delivered, mapped onto each north-star doc's claims, returning targeted edits where the doc no longer reflects the project's current shape. The archaeologist returns a structured list of `{ doc_id, proposed_edit }` entries plus any docs it concluded need no change.
4. **Carry the proposals into the confirm gate.** Edits aren't applied yet; they surface alongside the README/CLAUDE.md sweep for one approval pass.

If the archaeologist returns `failed` or surfaces a flagged fork it can't resolve cleanly, the synthesis line in the confirm gate names the failure and the gate offers to proceed without north-star edits or cancel. Forks worth a hosted decision get pointed at `/design` in the report.

### 4. Confirm — one approval gate

Present the complete package before writing:

```
/ship — <project or package name>
Version group:  <in-progress group_key>
Commits since <tag>: <N> (range: <tag>..HEAD)

Code bump:
  Proposed bump: <patch | minor | major>   (inferred — override with --patch/--minor/--major)
  New version:   <new-version>
  Files: <list of version-bearing files>

README / CLAUDE.md sweep:
  README.md          — <one-line change description>
  tab/CLAUDE.md      — <one-line change description>
  (or "no doc drift detected")

North-star KB edits (archaeologist synthesis vs. version brief):
  <doc title> [<doc_id>]      — <one-line proposed edit>
  <doc title> [<doc_id>]      — no change
  (or "no version brief found — synthesis skipped")

Brief deletion:
  <brief title> [<brief_id>]  — deleted on apply

Apply? (y / edit docs / skip docs / cancel)
```

Responses:
- `y` — proceed with everything as shown: code bump, README/CLAUDE.md edits, north-star KB edits, brief deletion.
- `edit docs` — inline edits to the proposed README/CLAUDE.md changes or the north-star edits.
- `skip docs` — apply the version bump and the brief deletion only; leave README, CLAUDE.md, and north-star docs untouched.
- `cancel` — write nothing, exit.

The confirm gate always shows all four items: code bump, README/CLAUDE.md sweep, north-star edits, brief deletion. `skip docs` skips the doc edits but still deletes the brief — the brief and the version are 1:1, and a shipped version with a lingering brief is the failure mode the convention exists to prevent.

### 5. Apply — write the bump, the docs, the brief deletion

On confirm:

1. **KB writes.** Apply the confirmed north-star edits via `update_document` per doc. Then delete the version brief. **Brief deletion is non-optional on apply** — the brief is 1:1 with the version, and once the version ships, the brief is gone. Git history is the historical record; the KB stays maintainable.
2. **Code edits.** Update the version file(s) the project uses. For this marketplace, that means **both** `.claude-plugin/marketplace.json` (the relevant plugin entry) **and** `<plugin>/.claude-plugin/plugin.json`. For other projects, update whatever file holds the version (`package.json`, `pyproject.toml`, `Cargo.toml`, etc.). Bump all of them in lockstep. Apply the confirmed README / CLAUDE.md edits in the same pass.
3. **Single git commit.** One commit containing the version bump, the README/CLAUDE.md edits, and any other on-disk changes. Conventional style, e.g.: `chore: release <new-version>`. Body lists the included sections and references the version brief that was deleted from the KB.
4. **Report.** Print the new version, the commit hash, the deleted brief's ID, the IDs of the north-star docs that were edited, and a one-line "ready to push" acknowledgement. The skill does not push.

### 6. Dry run

`--dry-run` stops before step 5 (Apply). Prints the plan — the bump, the README/CLAUDE.md sweep, the proposed north-star edits, and the brief that would be deleted — and exits without writing anything. Useful for previewing the synthesis pass.

## Output

- One commit on the current branch: version bump + confirmed README/CLAUDE.md edits.
- KB writes: north-star doc updates (when not skipped) + brief deletion (always, on apply).
- No push. No tag (tagging is the user's call unless project conventions require otherwise — if they do, name it in the report as the next step).
- A short report: new version, commit hash, deleted brief ID, edited north-star doc IDs, any docs that were skipped.

## Principles

- **One approval gate.** Code bump, README/CLAUDE.md sweep, north-star edits, and brief deletion all surface in a single confirm block. No staccato "can I edit this doc?" interruptions.
- **Commits and the brief are the truth.** The bump and the README/CLAUDE.md sweep read from `git log` and `git diff`; the north-star synthesis reads from the version brief. Both are observable artifacts, not memory.
- **Doc drift detection is heuristic, north-star synthesis is grounded.** The README/CLAUDE.md sweep flags candidates against commit signals; the archaeologist anchors north-star edits in the brief's contents. The user approves either way.
- **Brief deletion is non-optional on apply.** The brief is 1:1 with the version. A shipped version with a lingering brief is the convention's failure mode.
- **The user ships.** This skill stops at a clean commit. Pushing, tagging, merging — user's job.

## Constraints

- **No push. No force-push.** Ever.
- **No tag creation unless the project's convention requires it** (and even then, only on explicit user confirm).
- **No silent doc edits.** Every README, CLAUDE.md, or north-star edit passes through the confirm block.
- **No silent brief retention.** If apply runs, the brief is deleted. The only path that preserves the brief is `cancel`.
- **Version sync is atomic.** If a project has multiple files holding the version (e.g., marketplace + plugin manifests), bump all or none. A mismatch is worse than not shipping.
- **Stop if the working tree is dirty.** Uncommitted changes mean the sweep can't produce a clean result. Report the dirty state and stop.
- **No commit rewriting.** `/ship` adds a single new commit. It does not amend, squash, or rebase existing history.
- **No KB writes outside the apply step.** The synthesis pass surfaces edits; it doesn't write them. KB writes (north-star updates + brief deletion) only happen on `y`.

## What I need

- `tab-for-projects` MCP — `get_project_context` for the project and in-progress group inventory; `list_documents` (with `favorite: true`) for the north-star set; `search_documents` / `get_document` for the version brief lookup; `update_document` for the north-star edits; document-deletion capability for the brief (the brief is removed from the KB on apply).
- `archaeologist` subagent — runs north-star synthesis mode with the version brief and favorited docs as input; returns proposed edits per favorited doc.
- Git primitives (via `Bash`) — `git log`, `git diff`, `git tag` queries, and the single-commit `git commit` that lands the version bump and any on-disk doc edits.
- `Read`, `Edit`, `Grep`, `Glob` — for finding and touching README and nested CLAUDE.md files and the version-bearing manifest files.
- Environment — a git repo with at least one commit since the last version tag (or since initial commit if no tag exists), and a clean working tree on entry.
