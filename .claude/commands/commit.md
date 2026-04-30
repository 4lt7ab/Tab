---
description: Wrap the session — bump versions, audit CLAUDE.md, draft a commit.
argument-hint: [major|minor|patch]
---

Wrap up the current session and land it as a commit. Default bump is **patch**; if `$ARGUMENTS` contains `major` or `minor`, use that instead.

## 1. Survey

Run `git status` and `git diff` (staged + unstaged). If nothing has changed, stop and tell the user.

Note which trees the changes touch:

- `plugins/tab/` → bump `tab`
- repo-level only (`CLAUDE.md`, `scripts/`, `.claude/`, `cli/` outside the plugins) → no plugin bump

## 2. Bump versions

For each plugin whose tree was modified, increment per the chosen level in **both** files — the validator enforces they match:

- `plugins/<pkg>/.claude-plugin/plugin.json`
- `.claude-plugin/marketplace.json` (the matching entry in `plugins[]`)

If `cli/` was touched, also bump `cli/pyproject.toml`'s version per the same level.

## 3. Pass over CLAUDE.md

Read it and check two things:

- **Conciseness** — anything that recaps code, paraphrases SKILL.md behavior, or has bit-rotted since it was written? Tighten or cut. SKILL.md is canonical for skill behavior; CLAUDE.md should not duplicate it.
- **Commit-rules clarity** — the "Commit messages" section must stay load-bearing: short, wordplay over summary, ~40 chars, no conventional-commit prefix unless it's part of the joke. If the recent-calibration list has drifted from reality, refresh it from `git log --oneline -10`.

Only edit if there's a real win. A clean pass is fine — say so and move on.

## 4. Validate

`bash scripts/validate-plugins.sh` from the repo root. Fix any failures before committing.

## 5. Draft the commit

Write the message per CLAUDE.md's "Commit messages" rules. Riff on what actually changed — a pun, a callback, a phrase that fits the diff. Under ~40 chars. No conventional-commit prefix unless the joke needs it.

Show the draft to the user before committing. Let them redirect if the line doesn't land.

Once approved, stage the relevant files by name (never `git add -A`) and commit with the standard Claude Code co-author trailer via HEREDOC.
