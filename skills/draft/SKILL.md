---
name: draft
description: "Use when the user already knows *what* to build and needs exact proposed changes for *how* — says things like 'draft this', 'turn this into a plan', 'what's the implementation plan', 'how do I build this'. Not for exploration or brainstorming — the decisions should already be made."
argument-hint: "[source material — doc, idea, conversation topic]"
---

## What This Skill Does

Takes a decided plan — a workshop doc, brain dump, or settled idea — and produces a **Proposed Changes** document: an ordered, reviewable set of exact file edits with inline rationale. The output is iterative by design: propose → review → refine, as many passes as needed until the plan is ready to execute.

Not for exploration or design — decisions should already be made. This translates them into buildable precision.

## Output Directory

Tab writes to `<output-dir>/<topic>/draft-<concern>.md`. Tab always asks for the topic before writing and creates the directory if needed. Tab acts on the draft conversationally by default — writing to disk is for output worth persisting across sessions.

## How It Works

1. **Read the input.** Whatever source material the user provides — a document, a paragraph, a file, a conversation summary. If the input is a workshop document or other structured plan, anchor on its decisions rather than re-deriving them. Restate the objective in one sentence to confirm understanding.
2. **Ground the plan in real code.** The input tells you *what* to build. Research tells you *where* it goes and *what it touches* — exact files, real interfaces, actual values. This isn't rethinking the approach; it's making the approach precise enough to execute.
   - **Decompose into questions.** Before fanning out, name the specific questions that need answering. Not "research the codebase" — but "What does the auth middleware check?" or "What frontmatter fields do existing skills use?"
   - **Narrow subagent briefs.** Each subagent gets specific files to read and a specific question to answer. If a brief is broader than "read these files, answer this question," it's too broad.
   - **Synthesize before writing.** Assemble findings before generating steps. Catch gaps here — if a question isn't fully answered, send one more targeted query.
   - **Completion test:** Research is done when every step you're about to write references a real file, real value, or real interface. No placeholders.

   The right decomposition depends on the objective — name the pattern, don't prescribe a fixed list. Areas to investigate typically include:
   - **Directory structure and naming conventions** — how are things organized? What patterns do new files follow?
   - **Similar existing implementations** — find the closest analog to what's being built. Read it. The draft should mirror its patterns.
   - **Config and wiring files** — manifests, registries, index files, frontmatter references — anything that needs updating when a new thing is added.
   - **Dependencies and interfaces** — what does the new thing need to connect to? Read those interfaces so steps can reference exact function signatures, type shapes, or API contracts.
3. **Generate the draft.** Tab writes to `<output-dir>/<topic>/draft-<concern>.md` using the document structure below. Every change references actual project files, line numbers when useful, and concrete values — not placeholders.
4. **Present and iterate.** Summarize the plan conversationally — key phases, notable decisions, anything surprising. The user reviews and gives targeted feedback. Incorporate it and re-propose. The loop continues until the user is satisfied — there's no fixed number of rounds. If feedback reveals a gap that needs deeper investigation, don't stall — mark those steps with a severity note and finish the full plan:
   - `⚠️ uncertain` — plausible but unverified. Needs a codebase check.
   - `🚧 underspecified` — exists but lacks precision. Needs investigation.
   - `🛑 unresolved` — design decision missing. Can't write a precise step until it's made.

   The user gets a complete draft with known holes visible and sized, not half a draft.

## Document Structure

The draft is a pure execution plan. No research notes, no decision history, no open questions.

### Objective

One sentence. What we're building and why.

### Proposed Changes

Ordered, numbered, precise. Each change is something you can sit down and do without needing to investigate anything — the draft already did the investigating.

Changes include inline rationale via em-dash: state what changes and why it changes that way alongside each other. Example: `Update the description in frontmatter — reflects the iterative contract rather than the auditable-steps framing.`

Changes must include:
- **Exact file paths as markdown links** — not "the config file," but [agents/tab.md](agents/tab.md). Links use relative paths from the project root. This makes paths clickable in IDEs and reviewable in rendered markdown.
- **Concrete values** — not "add the appropriate entry," but "add `draft` to the `skills:` list"
- **Code snippets or content** when the change involves writing something non-obvious — show what to write, not just where to write it
- **Line references** when helpful — append to the link: [agents/tab.md:7](agents/tab.md#L7)

The precision test: could someone follow this change with zero familiarity with the codebase and get it right on the first try? If not, it needs more detail.

Bad: "Create a new skill file with the right frontmatter"
Good: "Create [skills/draft/SKILL.md](skills/draft/SKILL.md) with frontmatter: `name: draft`, `description: \"...\"`, `argument-hint: \"...\"` — matching the YAML frontmatter format used by existing skills"

Annotate changes where effort would surprise someone scanning the plan — not every change, just the surprising ones. Examples: `(heavy — requires migrating existing data)` or `(quick — one-line config change)`.

When a plan has distinct phases, use subheadings under Proposed Changes (`### Phase 1: Setup`, etc.). Number changes sequentially across phases. One document, not multiple files.

### Dependencies

Compact execution map showing sequencing at a glance:

> **Sequential:** 1 → 2 → 3
> **Parallel:** 4, 5, 6 (after 3)
> **Blocked:** 7 waits on external deploy

Human scans for shape. Claude uses for execution order. Only include this section if there are meaningful sequencing constraints.

### Out of Scope

Explicitly name what this plan does *not* cover, to prevent scope creep. If everything is in scope, omit this section.

### Example

````markdown
## Objective

Add a `lint` skill that runs ESLint with the project's config and reports results conversationally.

## Proposed Changes

### Phase 1: Skill setup

1. Create [skills/lint/SKILL.md](skills/lint/SKILL.md) with frontmatter:
   ```yaml
   name: lint
   description: "Run when the user asks to lint, check style, or clean up code."
   argument-hint: "[file or directory to lint]"
   ```
   *(quick — single file, follow [skills/draw-dino/SKILL.md](skills/draw-dino/SKILL.md) for structure)*

2. Register the skill in [agents/agent.md](agents/agent.md) — add `lint` to the `skills:` list in frontmatter (line 7) and add a row to the Skills table:
   ```
   | **lint** | `.agent/lint/` | Run ESLint and report results. |
   ```

### Phase 2: Skill logic

3. Write the skill body in `skills/lint/SKILL.md`. Core behavior:
   - Run `npx eslint <target> --format json` via Bash tool
   - Parse JSON output, group by severity
   - Summarize: file count, error count, top 3 recurring rules
   - Offer to auto-fix if all errors are auto-fixable (`--fix` flag)

4. Add error handling for missing ESLint config — check for `.eslintrc*` or `eslint.config.*` before running. If missing, tell the user and suggest `npx eslint --init`. *(heavy — needs to handle flat config vs. legacy config detection)*

## Dependencies

> **Sequential:** 1 → 2 (registration depends on file existing)
> **Parallel:** 3, 4 (after 2)

## Out of Scope

- Custom rule authoring — this skill runs existing config, doesn't modify it.
- Prettier integration — separate concern, separate skill if needed.
````

## Principles

- **Read the actual files.** A draft that says "follow existing patterns" has failed. Every change must reference real files (as markdown links), real values, real interfaces — because the skill read them, not because it assumed them.
- **Scope is explicit.** What's in and what's out are both stated clearly.
- **Split when it sprawls.** If the plan exceeds ~15 changes, break it into phases or suggest separate drafts per workstream. A plan too big to hold in your head isn't a plan.