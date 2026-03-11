# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.

## What This Is

Tab is a personal AI assistant defined entirely in markdown. No compiled code, no runtime, no dependencies, no build system. All behavior is defined through text files that an LLM reads and interprets.

Tab ships as a Claude Code plugin.

## Project Structure

```
agents/
  tab.md                ← Claude Code agent (persona, voice, rules, behaviors, status, skills via frontmatter)
skills/                 ← plugin-level skills discovered automatically from this path
  workshop/             ← collaborative idea workshopping and planning
  draft/                ← translates settled plans into proposed-changes docs
  feedback/             ← structured, graded feedback
  template/             ← guided interview to define reusable reference docs
  draw-dino/            ← ASCII art dinosaurs
.claude-plugin/
  plugin.json           ← plugin manifest for Claude Code
settings.json           ← activates Tab as the primary persona via agent ref
```

### Agent (`agents/tab.md`)

The Tab agent definition. Loaded automatically via `plugin.json`'s `"agents"` field. Defines persona, voice, rules, and behaviors. References all skills via `skills:` frontmatter. Maintains `.tab/status.md` for session-to-session orientation.

### Skills (`skills/`)

Each skill lives in `skills/<name>/SKILL.md`. Claude Code discovers them automatically from the path declared in `plugin.json`. The agent file maps each skill to its output directory — skill files use `<output-dir>` as a placeholder and never hardcode paths.

### Plugin wiring

- `plugin.json` declares the agent and skills paths.
- `settings.json` sets `"agent": "tab:Tab"` so Tab loads as the primary persona on install.

## Conventions

- **Naming**: lowercase, hyphenated for all directories (e.g., `draw-dino`, `workshop`).
- **Frontmatter**: SKILL.md files use YAML frontmatter with `name`, `description`, and optionally `argument-hint`. Agent files use `name`, `description`, and `skills` at minimum.
- **Skill triggers**: the `description` field in SKILL.md frontmatter doubles as the trigger condition. Write it as "Use when the user says X" (reactive), not "This skill does X" (descriptive).
- **Forked skills**: skills that can run autonomously (no back-and-forth with the user) should set `context: fork` in frontmatter. This runs the skill in an isolated subagent. Optionally pair with `agent: <type>` to select a specific subagent type (e.g., `Explore`, `Plan`, `general-purpose`). Most skills run inline — only fork when the skill does heavy research or autonomous work and doesn't need the conversation.
- **Skill output directories**: skills use `<output-dir>` as a placeholder. The agent resolves it — all skill output lands in `.tab/work/<topic>/`. Skill files should not hardcode output paths.
- **Git commits**: conventional prefixes (`feat:`, `fix:`, `docs:`, `refactor:`, `chore:`).
- **No code**: this project has no tests, no linting, no build. If you're writing code, you're in the wrong repo.
