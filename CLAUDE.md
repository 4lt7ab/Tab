# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.

## What This Is

Tab is a personal AI assistant defined entirely in markdown. No compiled code, no runtime, no dependencies, no build system. All behavior is defined through text files that an LLM reads and interprets.

Tab ships as a Claude Code plugin.

## Architecture: Hub-and-Spoke

Tab uses a hub-and-spoke model. Tab is the hub — the one agent users talk to. Specialists are subagents that Tab delegates to automatically based on the task. Users never switch agents or pick a persona. They talk to Tab, and Tab brings in help when it fits.

- **Skills** handle interactive work (conversation with the user). Workshop, feedback, draw-dino are skills. They run inline in Tab's context.
- **Specialists** handle autonomous work (task in, results out). Code review, implementation, test writing, PR summarization are specialists. They run in forks.

Rule of thumb: **conversation = skill. Autonomy = specialist.**

## Project Structure

```
agents/
  tab.md                ← main agent (hub, default, the persona)
  code-reviewer.md      ← specialist: reviews PRs and code changes
  implementer.md        ← specialist: implements changes in isolated worktrees from settled plans
  ...                   ← add specialists by dropping .md files here
skills/                 ← plugin-level skills discovered automatically
  workshop/             ← collaborative idea workshopping and planning
  feedback/             ← structured feedback
  draw-dino/            ← ASCII art dinosaurs
.claude-plugin/
  plugin.json           ← plugin manifest — lists agents explicitly, auto-discovers skills/
settings.json           ← activates Tab as the primary persona via agent ref
```

### Main Agent (`agents/tab.md`)

The Tab agent definition. Loaded as the primary persona via `settings.json`. Defines persona, voice, rules, and behaviors. References skills via `skills:` frontmatter. Orients on session start by scanning `.tab/work/` for topic directories.

### Specialists (`agents/<name>.md`)

Focused subagents — one task, one job. Each specialist must be listed in the `"agents"` array in `plugin.json`. Tab delegates to specialists automatically based on their `description` field. Specialists run in forks and return results to Tab.

### Skills (`skills/`)

Each skill lives in `skills/<name>/SKILL.md`. Claude Code discovers them automatically from the path declared in `plugin.json`. Skills that write files use `<output-dir>` as a placeholder — the agent resolves it at runtime. Not all skills write files; some (feedback, draw-dino) execute inline with no file output.

### Plugin wiring

- `plugin.json` lists agents explicitly in an array and auto-discovers skills from `./skills/`.
- `settings.json` sets `"agent": "tab:Tab"` so Tab loads as the primary persona on install.
- When adding a new specialist, you must add its path to the `"agents"` array in `plugin.json`.

## Adding a Specialist

1. Create a `.md` file in `agents/`.
2. Add its path to the `"agents"` array in `plugin.json`.

### Template

```yaml
# <name>.md
---
name: <name>
description: "<What it does>. <When to use it>."
context: fork
agent: general-purpose  # or: Explore, Plan
isolation: worktree     # optional — run in an isolated git worktree
model: sonnet           # optional — sonnet, opus, or haiku
background: true        # optional — run in background, notify on completion
permissionMode: acceptEdits  # optional — auto-accept file edits without prompting
---

<Instructions for the specialist. What it does, how it works, output format.>
```

Optional: add `skills: [tab:<skill-name>]` to inject skill definitions into the specialist's context at startup. No current specialists use this.

### Design principles

- **One specialist per task, not per domain.** `code-reviewer`, not `tab-coding`. Each specialist has a single, clear job.
- **Descriptions are routing contracts.** Two sentences max. First: what it does. Second: when to use it. Claude routes purely on LLM reasoning over descriptions — precision prevents misrouting.
- **No Tab persona.** Specialists don't inherit Tab's voice or personality. They can define their own tone if it serves the work, but they're not Tab.
- **Skill scoping is an allowlist.** Skills listed in frontmatter are injected into the specialist's context at startup. Skills not listed are not loaded.

### Naming

The name should read as a role or job title: `code-reviewer`, `implementer`, `test-writer`, `pr-summarizer`. Lowercase, hyphenated. No rigid formula — clarity beats convention.

### Description format

Two sentences. First: what it does. Second: when to use it.

```
"Review pull requests for quality and bugs. Use when the user asks for a code review or shares a diff."
"Write unit and integration tests for existing code. Use when the user asks for tests or test coverage."
```

### Overlap rule

If two specialists could both plausibly handle the same user request, sharpen the descriptions. The fix is always in the descriptions, not in routing logic.

### Dispatch patterns

Tab dispatches specialists and presents their output. The specialist never talks to the user directly. Dispatch uses the Skill tool with the specialist's name (e.g., `tab:implementer`) and a free-form brief containing all relevant context. Follow each specialist's own protocol — some require multiple dispatches.

- **Direct dispatch.** User request → Tab sends a brief → specialist returns output → Tab presents it. Used for standalone tasks (code review, implementation from a clear brief).
- **Workshop-driven dispatch.** Workshop produces a settled plan → Tab dispatches the specialist with that plan as the brief → specialist returns output → Tab presents it. Used when the work needed design thinking first.
- **Iteration.** Each dispatch is a fresh run — not a continuation. Include prior output and feedback in the new brief. Tab always mediates; the user never talks to the specialist directly.

## Conventions

- **Naming**: lowercase, hyphenated for all directories and specialist files (e.g., `draw-dino`, `code-reviewer`).
- **Frontmatter**: SKILL.md files use YAML frontmatter with `name`, `description`, and optionally `argument-hint`. The hub agent (`tab.md`) uses `name`, `description`, and `skills` at minimum. Specialist files use `name`, `description`, `context: fork`, and `agent`.
- **Skill triggers**: the `description` field in SKILL.md frontmatter doubles as the trigger condition. Write it as "Use when the user says X" (reactive), not "This skill does X" (descriptive).
- **Specialist triggers**: the `description` field is a routing contract. Write it as "<What it does>. <When to use it>."
- **Skills vs. specialists**: if the work is conversational (back-and-forth with the user), it's a skill. If it's autonomous (task in, results out), it's a specialist. Most autonomous work should be a specialist, not a forked skill.
- **Skill output directories**: file-writing skills use `<output-dir>` as a placeholder. The agent resolves it — output lands in `.tab/work/<topic>/`. Skills that execute inline (feedback, draw-dino) don't write files and don't use `<output-dir>`.
- **Skill-relative files**: skills can reference co-located files via `${CLAUDE_SKILL_DIR}/filename` in SKILL.md. No current skills use this, but it's available for skills that need templates, rubrics, or examples alongside their definition.
- **Git commits**: conventional prefixes (`feat:`, `fix:`, `docs:`, `refactor:`, `chore:`).
- **No code**: this project has no tests, no linting, no build. If you're writing code, you're in the wrong repo.
