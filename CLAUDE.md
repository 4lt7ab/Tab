# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.

## What This Is

Tab is a personal AI assistant defined entirely in markdown. No compiled code, no runtime, no dependencies, no build system. All behavior is defined through text files that an LLM reads and interprets.

Tab ships as a Claude Code plugin.

## The Principle

**Tab is a thinking partner.** It helps people think through problems, sharpen ideas, pressure-test plans, and make better decisions. It's not a task runner, not a code generator, not a personal assistant.

The core job: **help the user make their ideas better.**

Litmus test for new features:

- "Does this help the user think better?" — belongs.
- "Does this help the user do tasks faster?" — only if it's downstream of thinking.
- "Does this replace thinking?" — doesn't belong.

## Architecture

Tab is one agent (`tab.md`) with skills and specialists. Skills run inline in Tab's context. Specialists are sub-agents dispatched for autonomous work — they run in background with isolated context.

## Project Structure

```
agents/
  tab.md                ← the agent (persona, voice, rules, behaviors, dispatch logic)
  researcher.md         ← specialist: gathers context from codebases, web, and docs
  implementer.md        ← specialist: executes settled plans in isolated worktrees
  reviewer.md           ← specialist: reviews implementation against the plan
skills/                 ← discovered automatically
  workshop/             ← collaborative idea workshopping and planning
  draw-dino/            ← ASCII art dinosaurs
.claude-plugin/
  plugin.json           ← plugin manifest
settings.json           ← activates Tab as the primary persona
```

### Agent (`agents/tab.md`)

The agent definition — persona, voice, rules, runtime behaviors, and dispatch logic for specialists. Loaded as the primary persona via `settings.json`. This file is the single source of truth for how Tab behaves; don't restate its contents elsewhere.

Frontmatter fields: `name` (agent identity), `description` (one-line summary), `memory` (scope for persistent memory — `project` means memories are scoped to the project directory and shared via version control).

### Specialists (`agents/researcher.md`, `agents/implementer.md`, `agents/reviewer.md`)

Sub-agents that Tab dispatches when the thinking is done and autonomous work needs to happen. Each runs in background with a fresh context — the dispatch brief is their entire world. They serve the thinking, they don't replace it.

### Skills (`skills/`)

Each skill lives in `skills/<name>/SKILL.md`. Claude Code discovers them automatically from the path declared in `plugin.json`. Some skills produce artifacts; others (draw-dino) execute inline with no file output.

### Plugin wiring

- `plugin.json` lists all agents (Tab + specialists) and auto-discovers skills from `./skills/`.
- `settings.json` sets `"agent": "tab:Tab"` so Tab loads as the primary persona on install.

## Conventions

- **Frontmatter**: SKILL.md files use `name`, `description`, and optionally `argument-hint`.
- **Skill triggers**: the `description` field doubles as the trigger condition. A brief semantic frame ("Collaborative planning for non-trivial decisions") followed by reactive conditions ("Use when the user is exploring...") is more effective than either alone. Lead with what the skill is, then specify when to fire.
- **Skill output**: skills that produce artifacts write them wherever makes sense for the project. Inline skills (draw-dino) don't write files.
- **Skill-relative files**: skills can reference co-located files via `${CLAUDE_SKILL_DIR}/filename` in SKILL.md.
- **Git commits**: conventional prefixes (`feat:`, `fix:`, `docs:`, `refactor:`, `chore:`).
- **No code**: this project has no tests, no linting, no build. If you're writing code, you're in the wrong repo.
