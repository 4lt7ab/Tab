---
name: grimoire
description: "Help the user run their own grimoire — add, search, and craft content that searches well by both meaning and keyword. Use when the user wants grimoire as a utility on their data."
argument-hint: "[task]"
---

# Grimoire

Help the user use grimoire as a utility — a single-file SQLite + sqlite-vec datastore for vector and keyword search over their own records. Tab's main job here is content authoring: a record's `content` field is what the embedder *and* FTS5 both see, and writing it well is a craft.

This is **not** `cairn`. `cairn` recalls Tab's own past thinking from his own grimoires. This skill is helping the user run *their* grimoire on *their* data.

## Trigger

**When to activate:**
- "Add this to my grimoire" / "ingest these into a grimoire"
- "Search my grimoire for X" / "what's in my grimoire about Y"
- "Help me write the content for this entry"
- "Set up a grimoire for <topic>"
- Any clear "use grimoire as a tool on my data" intent

**When NOT to activate:**
- "Do you remember what I said about X" → that's `cairn`
- General question about how grimoire works → just answer
- User wants to write a grimoire-shaped feature in their own code → just code

## Bootstrap

Two checks via Bash before doing anything:

1. **CLI installed.** `grimoire --version`. If missing, print and stop:

   ```sh
   uv tool install '4lt7ab-grimoire-cli[fastembed]'
   # or: pipx install '4lt7ab-grimoire-cli[fastembed]'
   ```

2. **Mount resolved.** `grimoire info`. If it errors, decide with the user.

   The default mount is `.grimoire/` in the current working directory — that's the convention, and it's already git-ignored by grimoire's setup docs. Don't invent a mount somewhere else (`~/.grimoire`, `/tmp/...`) unless the user asks for it.

   - **New grimoire (default path):**

     ```sh
     mkdir -p .grimoire
     export GRIMOIRE_MOUNT=$PWD/.grimoire
     grimoire init
     ```

     Then make sure `.grimoire/` is git-ignored — the SQLite file and the embedder model cache (`models/`, ~30MB+) don't belong in version control. Check the project's `.gitignore`:

     - Exists, missing `.grimoire/` → append it (`echo '.grimoire/' >> .gitignore`).
     - Exists, already has `.grimoire/` (or a parent glob covering it) → leave alone.
     - Doesn't exist → ask before creating one. Adding `.gitignore` to a repo that doesn't have one is a project-wide decision.
     - Not a git repo → skip; mention it once so the user knows.

   - **Existing mount elsewhere** → `export GRIMOIRE_MOUNT=<path>` for this shell, then re-run `grimoire info` to confirm. The user has presumably already gitignored their custom location; don't touch it.

   `info` is the cheap probe — no embedder load.

## Authoring content

The highest-leverage thing Tab does in this skill is help the user write good `content` strings. The model:

- **`content`** — text the embedder embeds *and* FTS5 indexes. The description.
- **`payload`** — optional structured object returned alongside a hit. The thing the description points at.

A query (vector or keyword) hits `content`; the user gets `payload` back. `content` carries every token a future search might use to find this record, written so the embedder can also place it semantically.

**Heuristics for good content:**

- **Describe, don't name.** `"Wraps the caster in a curtain of silence so footfalls vanish"` beats `"Hush spell"` — keyword-searchable for "silence", "footfalls", and semantically near "stealth", "muffle", "quiet".
- **Include the literal tokens a user will search for.** Proper nouns, IDs, technical terms, obvious surface words. Vector search is forgiving; keyword search is not.
- **Vary phrasing where natural.** Two verbs covering the same idea give the embedder more surface and FTS5 more hooks. Don't pad — every word earns its slot.
- **Prose in `content`, structure in `payload`.** IDs, enums, numbers belong in `payload`. Don't stuff JSON-shaped strings into `content`.

When asked to write content for an entry, offer 1–3 candidate strings, name what each optimizes for, and let the user pick.

## Operations

All commands run via Bash with `GRIMOIRE_MOUNT` exported.

**One-off add:**

```sh
grimoire add "<content>" --kind <kind> --payload '<json>'
```

**Batch ingest from JSONL** — preferred for more than ~3 entries. Write the JSONL to `$GRIMOIRE_MOUNT/<name>.jsonl`, one record per line:

```jsonl
{"kind": "...", "content": "...", "payload": {...}}
```

Then `grimoire ingest <path>.jsonl`.

**Search:**

- `grimoire vector-search "<phrase>" --kind <k>` — by meaning.
- `grimoire keyword-search "<tokens>" --kind <k>` — literal, FTS5 syntax (phrases, prefix, boolean).
- Run both when the user's intent is fuzzy — they often complement each other.

**Inspect:** `grimoire info` for model/dimension/entry count/kinds. `grimoire list | jq` for chronological browsing. Pipe any read command to `jq` if the user wants pretty output.

## Principles

- **Search hits `content`, not `payload`.** A common mistake is dumping structure into `content` and leaving the description thin. Push back when you see it.
- **Kind is a partition, not a tag.** Use it for genuinely different record types (`spell` vs `creature`), not for sub-categories of one type. Filter by kind, search across kinds.
- **One file, one model.** A grimoire is locked to its embedder on init. If `grimoire info` shows a different model than the user expects, surface the mismatch — don't paper over it.
- **Don't invent payloads.** If the user gives content but no payload, ask before fabricating IDs or fields. An entry without a payload is fine — the content itself is what comes back.
