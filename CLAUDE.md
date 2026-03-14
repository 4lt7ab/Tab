# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.

## What This Is

Tab is a personal AI assistant defined entirely in markdown. No compiled code, no runtime, no dependencies, no build system. All behavior is defined through text files that an LLM reads and interprets.

Tab ships as a Claude Code plugin.

## The Principle

**Tab is a thinking partner.** It helps people think through problems, sharpen ideas, pressure-test plans, and make better decisions. It's not a task runner, not a code generator, not a personal assistant. When Tab executes — dispatching an implementer, reviewing code — that execution serves the thinking. The downstream consequence of ideas that are ready, not the primary offering.

The core job: **help the user make their ideas better.**

Litmus test for new features:

- "Does this help the user think better?" — belongs.
- "Does this help the user do tasks faster?" — only if it's downstream of thinking.
- "Does this replace thinking?" — doesn't belong.

## Architecture: Hub-and-Spoke

Tab uses a hub-and-spoke model. The hub agent (`tab.md`) is the user-facing entry point. Specialists are subagents dispatched via fork based on their `description` field.

- **Skills** are Tab's core offering — thinking *with* the user. Workshop, feedback, collaborative refinement. These run inline in the hub agent's context. Skills are what Tab *is*.
- **Specialists** are Tab's hands — working *for* the user, after thinking is done. These run in forks. Task in, results out. Specialists serve the thinking process; they don't define it.
- **Researcher** straddles the line — it supports thinking directly by gathering context, finding prior art, and answering questions that need real research before Tab can give a good answer.

Rule of thumb: **conversation = skill. Autonomy = specialist. Research = thinking support.**

## Project Structure

```
agents/
  tab.md                ← main agent (hub, default, the persona)
  code-reviewer.md      ← specialist: reviews PRs and code changes
  implementer.md        ← specialist: implements changes in isolated worktrees from settled plans
  researcher.md         ← specialist: researches topics via codebase scanning and web search
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

Each skill lives in `skills/<name>/SKILL.md`. Claude Code discovers them automatically from the path declared in `plugin.json`. Not all skills write files; some (feedback, draw-dino) execute inline with no file output. File-writing skills use their own output directories (e.g., `.tab/work/<topic>/`).

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

Optional: add `skills: [tab:<skill-name>]` to inject skill definitions into the specialist's context at startup.

### Design principles

- **One specialist per task, not per domain.** `code-reviewer`, not `tab-coding`.
- **Descriptions are routing contracts.** Two sentences: what it does, when to use it. Claude routes on descriptions alone — precision prevents misrouting. If two specialists overlap, sharpen the descriptions.
- **No Tab persona.** Specialists can define their own tone, but they're not Tab.
- **Name as a role.** `code-reviewer`, `implementer`, `test-writer`. Lowercase, hyphenated.
- Dispatch behavior is defined in `tab.md`; don't restate it here.

## Conventions

- **Frontmatter**: SKILL.md files use `name`, `description`, and optionally `argument-hint`. Specialist files use `name`, `description`, `context: fork`, and `agent`.
- **Skill triggers**: the `description` field doubles as the trigger condition. Write it as "Use when the user says X" (reactive), not "This skill does X" (descriptive).
- **Skill output**: file-writing skills use `.tab/work/<topic>/`. Inline skills (feedback, draw-dino) don't write files.
- **Skill-relative files**: skills can reference co-located files via `${CLAUDE_SKILL_DIR}/filename` in SKILL.md.
- **Git commits**: conventional prefixes (`feat:`, `fix:`, `docs:`, `refactor:`, `chore:`).
- **No code**: this project has no tests, no linting, no build. If you're writing code, you're in the wrong repo.
