---
name: ship
description: Pre-push sweep — surface likely-stale docs (README, CLAUDE.md) for confirmation and apply a version bump in a single commit. Does not push. Use when work is committed and the branch is ready to go out. Triggers on `/ship` and phrases like "cut a version", "get this ready to push", "run the ship sweep".
argument-hint: "[--patch | --minor | --major] [--dry-run]"
---

A pre-push checkpoint. `/ship` reads the commits since the last version tag, surfaces documentation that looks stale against the diff, and — on user confirmation — applies a version bump plus any confirmed doc updates in a single commit. It never pushes. The user ships.

## Trigger

**When to activate:**
- User invokes `/ship`, optionally with a bump hint (`--patch`, `--minor`, `--major`).
- User says "cut a version", "get this ready to push", "run the ship sweep", "prep for release".
- Work just completed via `/work` and the user wants to package it.

**When NOT to activate:**
- No commits since the last version tag — there's nothing to ship. Say so and stop.
- User is mid-work and hasn't committed — the sweep needs commits to read. Point them back to `/work` or direct commits.
- User wants to push — this skill stops at the commit. Pushing is the user's call.

## Requires

- **Tool:** `Bash` — for `git log`, `git diff`, tag queries, and applying the version bump commit.
- **Tool:** `Read`, `Edit`, `Grep`, `Glob` — for finding and touching README and nested CLAUDE.md files.
- **Environment:** a git repo with at least one commit since the last version tag (or since initial commit if no tag exists).

## Behavior

The skill flows in four phases: **Scan** (find the commit range), **Sweep** (surface stale docs), **Confirm** (one approval gate), **Apply** (write the bump + doc updates in a single commit).

### 1. Scan — determine the commit range

1. Find the last version tag. Priority: nearest tag on current branch matching a semver-ish pattern (`v1.2.3`, `1.2.3`, or plugin-prefixed like `tab-for-projects-2.3.0`). Fall back to initial commit if no tag exists.
2. Read commits since the tag with `git log <tag>..HEAD --oneline --no-merges`.
3. If the range is empty, say so and stop. Nothing to ship.
4. Read the full diff with `git diff <tag>..HEAD --stat` to get the file list for the doc sweep.
5. Infer a version bump from commit types:
   - `breaking:` or `!:` in any subject → **major**
   - `feat:` / `add:` present → **minor**
   - `fix:` / `chore:` / `refactor:` / anything else → **patch**
   - A CLI flag (`--patch`, `--minor`, `--major`) overrides the inference.

### 2. Sweep — surface likely-stale docs

From the diff's file list, identify docs that plausibly need updating:

- **README.md** (at any depth) is stale if: user-facing features were added/removed, CLI invocations changed, installation steps changed, or the file is named in the diff. Scan commit subjects for these signals.
- **CLAUDE.md** (at any depth) is stale if: a new module was added, an agent/skill was added or renamed, conventions changed, or the structure-tree portion doesn't match the filesystem.

For each doc the sweep flags, Read it and propose a targeted edit — not a rewrite. The user confirms, edits, or skips per-doc.

If no docs look stale, say so — "No README / CLAUDE.md drift detected." The sweep is allowed to find nothing.

### 3. Confirm — one approval gate

Present the complete package before writing:

```
/ship — <project or package name>
Commits since <tag>: <N> (range: <tag>..HEAD)

Proposed bump: <patch | minor | major>   (inferred from commits — override with --patch/--minor/--major)
New version:   <new-version>

Doc updates:
  README.md          — <one-line change description>
  tab/CLAUDE.md      — <one-line change description>
  (or "no doc drift detected")

Apply? (y / edit docs / skip docs / cancel)
```

Responses:
- `y` — proceed with everything as shown.
- `edit docs` — inline edits to the proposed doc changes.
- `skip docs` — apply version only; leave docs untouched.
- `cancel` — write nothing, exit.

### 4. Apply — write the bump and the docs

On confirm:

1. **Version bump.** Update the version file(s) the project uses. For this marketplace, that means **both** `.claude-plugin/marketplace.json` (the relevant plugin entry) **and** `<plugin>/.claude-plugin/plugin.json`. For other projects, update whatever file holds the version (`package.json`, `pyproject.toml`, `Cargo.toml`, etc.). Bump all of them in lockstep.
2. **Doc updates.** Apply the confirmed doc edits (or skip if the user said `skip docs`).
3. **Commit.** One commit containing the version bump and any doc edits. Conventional style, e.g.: `chore: release <new-version>`. Body lists the included sections.
4. **Report.** Print the new version, the commit hash, and a one-line "ready to push" acknowledgement. The skill does not push.

### 5. Dry run

`--dry-run` stops before step 4 of Apply. Prints the plan and the diff of what would be written, does not commit.

## Output

- One commit on the current branch: version bump + any confirmed doc edits.
- No push. No tag (tagging is the user's call unless project conventions require otherwise — if they do, name it in the report as the next step).
- A short report: new version, commit hash, any docs that were skipped.

## Principles

- **One approval gate.** Everything the sweep found surfaces in a single confirm block. No staccato "can I edit this doc?" interruptions.
- **Commits are the truth.** The bump and the doc sweep both read from `git log` and `git diff`, not from memory. If the commits are sparse or cryptic, the output will show it — that's a signal to the user, not a reason to embellish.
- **Doc drift detection is heuristic.** The sweep flags candidates; the user approves. A missed doc is the user's call, not a silent failure.
- **The user ships.** This skill stops at a clean commit. Pushing, tagging, merging — user's job.

## Constraints

- **No push. No force-push.** Ever.
- **No tag creation unless the project's convention requires it** (and even then, only on explicit user confirm).
- **No silent doc edits.** Every doc change passes through the confirm block.
- **Version sync is atomic.** If a project has multiple files holding the version (e.g., marketplace + plugin manifests), bump all or none. A mismatch is worse than not shipping.
- **Stop if the working tree is dirty.** Uncommitted changes mean the sweep can't produce a clean result. Report the dirty state and stop.
- **No commit rewriting.** `/ship` adds a single new commit. It does not amend, squash, or rebase existing history.
