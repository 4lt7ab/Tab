# CLAUDE.md

**TL;DR:** Tab is personality, workflows, and skills as plain markdown. A Claude Code plugin (`plugins/tab/`) and a Python CLI (`cli/`) both read the same substrate. The markdown is the source of truth; the runtimes load it.

## Where to look

| If you need to... | Read |
|---|---|
| Understand the system | [docs/architecture.md](docs/architecture.md) |
| Set up locally | [docs/setup.md](docs/setup.md) |
| Run or write tests | [docs/testing.md](docs/testing.md) |
| Cut a release | [docs/deployment.md](docs/deployment.md) |
| Match the codebase style | [docs/conventions.md](docs/conventions.md) |
| Understand why something is the way it is | [docs/decisions.md](docs/decisions.md) |
| Edit the CLI runtime | [cli/MAINTENANCE.md](cli/MAINTENANCE.md) |

## Rules

All files in `.claude/rules/` apply to this repo. Read them.

- [commit-messages](.claude/rules/commit-messages.md) — wordplay over summary, under ~40 chars
- [never-bump-versions](.claude/rules/never-bump-versions.md) — versions move only via `just bump`
- [python-tooling](.claude/rules/python-tooling.md) — uv only, never pip / python3
- [skill-and-agent-frontmatter](.claude/rules/skill-and-agent-frontmatter.md) — `name`, `description`, optional `argument-hint`
- [destructive-git](.claude/rules/destructive-git.md) — confirm before reset --hard / push --force / branch delete

## Project-specific notes

The Tab plugin in `plugins/tab/` is what this repo *ships*. The `.claude/` directory is for working *on* the repo. Don't paraphrase skill behavior into this file or any doc — `SKILL.md` is canonical, and recaps bit-rot.

The validator's CLAUDE.md tree check is a soft substring presence check: every skill `skills/<name>/SKILL.md` and every agent `agents/<name>` must appear somewhere in this file. Tree-art whitespace and box-drawing characters are decorative — don't repair them.

## Substrate (validator-required paths)

These paths must appear somewhere in this file. The validator greps for them.

```
plugins/tab/agents/tab.md
plugins/tab/skills/draw-dino/SKILL.md
plugins/tab/skills/hey-tab/SKILL.md
plugins/tab/skills/listen/SKILL.md
plugins/tab/skills/teach/SKILL.md
plugins/tab/skills/think/SKILL.md
```

CLI-only skill (registry-validated, not in the marketplace):

```
cli/src/tab_cli/skills/cairn/SKILL.md
```
