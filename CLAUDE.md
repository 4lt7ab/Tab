# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.

## What This Is

Tab is a personal AI assistant defined entirely in markdown. No compiled code, no runtime, no dependencies, no build system. All behavior is defined through text files that an LLM reads and interprets.

Tab ships as a Claude Code plugin.

## Architecture: Hub-and-Spoke

Tab uses a hub-and-spoke model. The hub agent (`tab.md`) is the user-facing entry point. Specialists are subagents dispatched via fork based on their `description` field.

- **Skills** run inline in the hub agent's context. They handle interactive, conversational work.
- **Specialists** run in forks. They handle autonomous work — task in, results out.

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

The hub agent definition — persona, voice, rules, and runtime behaviors. Loaded as the primary persona via `settings.json`. This file is the single source of truth for how the hub agent behaves; don't restate its contents elsewhere.

### Specialists (`agents/<name>.md`)

Focused subagents — one task, one job. Each specialist must be listed in the `"agents"` array in `plugin.json`. The hub agent dispatches specialists based on their `description` field. Specialists run in forks and return results to the hub.

### Skills (`skills/`)

Each skill lives in `skills/<name>/SKILL.md`. Claude Code discovers them automatically from the path declared in `plugin.json`. Not all skills write files; some (feedback, draw-dino) execute inline with no file output. File-writing skills use their own output directories (e.g., `workshop/<topic>/`).

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

### Dispatch

Specialists are dispatched via the Skill tool using their name (e.g., `tab:implementer`) and a free-form brief. Each dispatch is a fresh run — not a continuation. Dispatch behavior is defined in `tab.md`; don't restate it here.

## Conventions

- **Naming**: lowercase, hyphenated for all directories and specialist files (e.g., `draw-dino`, `code-reviewer`).
- **Frontmatter**: SKILL.md files use YAML frontmatter with `name`, `description`, and optionally `argument-hint`. The hub agent (`tab.md`) uses `name`, `description`, and `skills` at minimum. Specialist files use `name`, `description`, `context: fork`, and `agent`.
- **Skill triggers**: the `description` field in SKILL.md frontmatter doubles as the trigger condition. Write it as "Use when the user says X" (reactive), not "This skill does X" (descriptive).
- **Specialist triggers**: the `description` field is a routing contract. Write it as "<What it does>. <When to use it>."
- **Skills vs. specialists**: if the work is conversational (back-and-forth with the user), it's a skill. If it's autonomous (task in, results out), it's a specialist. Most autonomous work should be a specialist, not a forked skill.
- **Skill output directories**: file-writing skills use their own output directories (e.g., `workshop/<topic>/`). Skills that execute inline (feedback, draw-dino) don't write files.
- **Skill-relative files**: skills can reference co-located files via `${CLAUDE_SKILL_DIR}/filename` in SKILL.md. No current skills use this, but it's available for skills that need templates, rubrics, or examples alongside their definition.
- **Git commits**: conventional prefixes (`feat:`, `fix:`, `docs:`, `refactor:`, `chore:`).
- **No code**: this project has no tests, no linting, no build. If you're writing code, you're in the wrong repo.
