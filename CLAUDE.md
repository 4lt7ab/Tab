# CLAUDE.md

This file provides guidance to Claude Code when working in this repository.

## The Principle

**Tab is a thinking partner.** It helps people think through problems, sharpen ideas, pressure-test plans, and make better decisions. Specialists handle execution, but only downstream of thinking — never instead of it.

Litmus test for changes:

- "Does this help the user think better?" — belongs.
- "Does this help the user do tasks faster?" — only if it's downstream of thinking.
- "Does this replace thinking?" — doesn't belong.

## Architecture

Tab is one agent (`tab.md`) with skills and specialists. Skills run inline in Tab's context. Specialists are sub-agents dispatched for autonomous work — they run in background with isolated context. `tab.md` is the single source of truth for how Tab behaves; don't restate its contents elsewhere.

```
agents/
  tab.md                ← the agent (persona, voice, rules, behaviors, dispatch logic)
  researcher.md         ← specialist: context gathering
  implementer.md        ← specialist: plan execution in isolated worktrees
  reviewer.md           ← specialist: implementation review against plan
skills/                 ← auto-discovered from path in plugin.json
  workshop/             ← collaborative planning
  draw-dino/            ← ASCII art dinosaurs (easter egg)
  log/                  ← deferred work tracking (docs/maintenance/)
docs/
  maintenance/              ← deferred work items, one file per item (team-facing)
.claude-plugin/
  plugin.json           ← plugin manifest
settings.json           ← sets Tab as primary persona on install
```

### Plugin Wiring

- `plugin.json` registers all agents and auto-discovers skills from `./skills/`.
- `settings.json` sets `"agent": "tab:Tab"` so Tab loads as the primary persona. The Claude Code plugin system only supports the `agent` key in plugin `settings.json` — any other keys are silently ignored. Permissions belong in the user's own `.claude/settings.json`.

### Agent Frontmatter

Agent `.md` files use YAML frontmatter:
- `name` — identity
- `description` — one-line summary + trigger conditions (doubles as the dispatch trigger for specialists)
- `memory` — scope; `project` means shared via version control (tab.md only)
- `model` — `sonnet` or `opus`; omit to use the user's default
- `background: true` — runs as a background sub-agent (all specialists; omit for the primary persona)
- `isolation: worktree` — runs in an isolated git worktree (implementer only)

### Skill Frontmatter

SKILL.md files use: `name` (lowercase, hyphenated, matches directory), `description` (trigger condition), and optionally `argument-hint`.

## Conventions

- **Trigger descriptions**: the `description` field in both agent and skill frontmatter doubles as the trigger condition. Lead with a semantic frame ("Collaborative planning for non-trivial decisions"), follow with reactive conditions ("Use when the user is exploring..."). This convention applies to specialists too, not just skills.
- **Skill-relative files**: skills can reference co-located files via `${CLAUDE_SKILL_DIR}/filename` in SKILL.md.
- **Skill output**: skills that produce artifacts write them wherever makes sense for the project. Inline skills don't write files.
- **Git commits**: conventional prefixes — `feat:`, `fix:`, `docs:`, `refactor:`, `chore:`.
- **Dash style**: use em dashes (`—`) throughout, not double hyphens (`--`).
- **No code**: this project has no tests, no linting, no build. If you're writing code, you're in the wrong repo.
