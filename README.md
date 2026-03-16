# Tab™

A thinking partner defined entirely in markdown. No compiled code, no dependencies, no build system — just text files that shape how Claude talks, thinks, and works with you.

Tab ships as a **Claude Code plugin**.

---

## Install

Install Tab from the Claude Code plugin marketplace. Tab activates automatically — no setup commands needed.

### Recommended Permissions

Tab works out of the box with default Claude Code permissions (you'll be prompted for each tool use). For a smoother experience, add this to your project's `.claude/settings.json`:

```json
{
  "permissions": {
    "allow": [
      "Bash",
      "Read(**)",
      "Write(**)",
      "Edit(**)",
      "Agent(*)"
    ],
    "deny": [
      "Bash(rm -rf *)",
      "Bash(sudo *)",
      "Bash(git push *)"
    ]
  }
}
```

This is a minimal starting point. See [`docs/recommended-settings.json`](docs/recommended-settings.json) for the full recommended configuration. Customize to taste.

---

## Quick Start

Talk to Tab like a person. No special syntax needed. Tab picks up on intent and activates the right skill.

```
You:  Hey Tab
Tab:  [responds in character, orients you on what's happening]

You:  Let's workshop a notification system
Tab:  [researches the landscape, lays out a rough plan, iterates with you until it's solid]

You:  Send it to the implementer
Tab:  [dispatches the plan to a specialist in an isolated worktree, reviews the output when it's done]
```

---

## Specialists

Tab dispatches specialist sub-agents for autonomous work. They run in the background with isolated context — Tab does the thinking, specialists do the doing.

- **Researcher** — gathers context from codebases, web, and docs. Dispatched when Tab needs information it doesn't have.
- **Implementer** — executes a settled plan in an isolated git worktree. Only dispatched after design questions are resolved and you confirm.
- **Reviewer** — reviews implementation against the plan that produced it. Runs automatically after the implementer finishes.

You can dispatch them explicitly ("have the researcher look into X", "research this") or Tab will suggest dispatch when the work is ready for it.

---

## Skills

Skills activate automatically based on what you say, or you can invoke them directly with slash commands.

### workshop

**Slash command:** `/workshop [idea or problem]`

Sustained collaborative planning. Tab researches the landscape, lays down a rough plan, then iterates with you — reacting to feedback, pressure-testing assumptions, and updating a living document as decisions land. The workshop is done when all open questions are resolved.

### draw-dino

**Slash command:** `/draw-dino [species]`

ASCII art dinosaurs. An easter egg that lowers the barrier to interaction — if someone will ask for a dinosaur, they'll ask for anything. Customizable by mood: cute/baby, flying (pterodactyl), scary/fierce (T-Rex), big/gentle (brontosaurus). Includes a fun fact with each drawing.

---

## For Contributors

### Adding a Skill

1. Create `skills/my-skill/SKILL.md` with YAML frontmatter:

```yaml
---
name: my-skill
description: "What the skill does. Use when [trigger conditions]."
argument-hint: "[optional args]"
---
```

2. Write the body — workflow, instructions, constraints.

3. That's it. Claude Code discovers skills automatically. No registration needed.

See `CLAUDE.md` for architecture details, conventions, and guidance for AI-assisted development.

---

## Trademark

Tab™ is a trademark of Jacob Fjermestad (AltT4b), used to identify the Tab AI persona, agent, and associated personality definition files. This trademark applies specifically to the use of "Tab" as the name of an AI assistant, AI agent, AI persona, or AI-powered software product.

The Apache 2.0 license grants permission to use, modify, and distribute the source files in this repository. It does not grant permission to use the Tab™ name, branding, or persona identity to market, distribute, or represent a derivative work as "Tab" or as affiliated with the Tab project.

If you fork or modify this project, please choose a different name for your derivative.
