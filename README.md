# Tab™

A personal AI assistant defined entirely in markdown. No compiled code, no dependencies, no build system -- just text files that shape how Claude talks, thinks, and works with you.

Tab ships as a **Claude Code plugin**.

---

## Install

Install Tab from the Claude Code plugin marketplace. Tab activates automatically -- no setup commands needed.

---

## Quick Start

Talk to Tab like a person. No special syntax needed. Tab picks up on intent and activates the right skill.

```
You:  Hey Tab
Tab:  [responds in character, orients you on what's happening]

You:  Let's workshop a notification system
Tab:  [researches the landscape, lays out a rough plan, iterates with you until it's solid]

You:  What's in flight?
Tab:  [checks status, tells you what's active and what's next]

You:  Draw me a scary dinosaur
Tab:  [ASCII art T-Rex with a fun dino fact]
```

---

## Skills

Tab comes packaged with Skills. Skills activate automatically based on what you say, or you can invoke them directly with slash commands. Built-in behaviors (greeting, status tracking) are part of the agent definition and don't need separate skill files.

### workshop

**Slash command:** `/workshop [idea or problem]`

Sustained collaborative planning. Tab researches the landscape (web search, codebase exploration), lays down a rough plan, then iterates with you in an open loop -- reacting to your feedback, researching before proposing, and updating a living document as decisions land. The session ends when you say it does, and the final doc is restructured so a cold reader could implement from it. Output goes to `.tab/work/<topic>/plan.md`.

### feedback

**Slash command:** `/feedback [artifact or idea]`

Structured, graded (A-F) feedback on code, prose, plans, or ideas. Leads with a letter grade, skips nitpicks, groups feedback by importance.

### draw-dino

**Slash command:** `/draw-dino [species]`

ASCII art dinosaurs. Customizable by mood: cute/baby, flying (pterodactyl), scary/fierce (T-Rex), big/gentle (brontosaurus). Includes a fun fact with each drawing.

### Built-in: Greeting

Tab greets and orients on session start. Introduces itself to new users, or picks up where things left off with returning users.

---

## For Contributors

### Project Layout

```
agents/
  tab.md                # Main agent — hub, persona, skills via frontmatter
  code-reviewer.md      # Specialist: reviews PRs and code changes
  implementer.md        # Specialist: implements changes in isolated worktrees
  researcher.md         # Specialist: deep research across codebases and the web
skills/
  workshop/SKILL.md     # Collaborative idea workshopping and planning
  feedback/SKILL.md     # Structured, graded feedback
  draw-dino/SKILL.md    # ASCII art dinosaurs
.claude-plugin/
  plugin.json           # Plugin manifest — lists agents, auto-discovers skills
settings.json           # Activates Tab as the primary persona
```

### How Agents Work

**`agents/tab.md`** is the main agent (the hub). Its YAML frontmatter declares identity and lists skills (`tab:feedback`, `tab:workshop`, `tab:draw-dino`). The body defines voice, rules, and behaviors.

**Specialists** (`agents/code-reviewer.md`, `agents/implementer.md`, `agents/researcher.md`) are focused subagents — one task, one job. Tab delegates to them automatically based on the task. They run in forks and return results to Tab; the user never interacts with them directly. Each specialist must be listed in the `"agents"` array in `plugin.json`.

**`settings.json`** at the plugin root sets `"agent": "tab:Tab"`, which tells Claude Code to load Tab as the primary persona. This is the mechanism that makes Tab "just work" after install -- no setup commands needed.


### How Skills Work

Each skill lives in `skills/<name>/SKILL.md` with YAML frontmatter:

```yaml
---
name: draw-dino
description: "Use when the user asks for a dinosaur, says 'rawr', or..."
argument-hint: "[species]"
---
```

- **`name`** -- lowercase, hyphenated. Matches the directory name.
- **`description`** -- doubles as the **trigger condition**. Write it as "Use when the user says X" (reactive), not "This skill does X" (descriptive). The description tells the model *when* to activate; the body tells it *what* to do.
- **`argument-hint`** -- optional. Hints at accepted arguments.

Skills that produce file output write to `.tab/work/<topic>/`.

### Add a New Skill

1. **Create the directory:** `skills/my-skill/SKILL.md`

2. **Write frontmatter** with `name`, `description` (as trigger condition), and optionally `argument-hint`.

3. **Write the body.** Define workflow, instructions, constraints. Start with a "What This Skill Does" section.

4. **Register in the agent.** Add `tab:my-skill` to the `skills:` list in `agents/tab.md` frontmatter. (You don't need to touch `plugin.json` -- Claude Code discovers skills automatically from the `skills/` path.)

5. **If it needs scripts or assets**, put them alongside `SKILL.md` in the skill directory.

### Conventions

- **Naming:** lowercase, hyphenated directories and files.
- **Git commits:** conventional prefixes -- `feat:`, `fix:`, `docs:`, `refactor:`, `chore:`.
- **Output:** all skill output goes to `.tab/work/<topic>/`.
- **No code:** this project has no tests, no linting, no build. If you're writing code, you're in the wrong repo.

---

## Trademark

Tab™ is a trademark of Jacob Fjermestad (AltT4b), used to identify the Tab AI persona, agent, and associated personality definition files. This trademark applies specifically to the use of "Tab" as the name of an AI assistant, AI agent, AI persona, or AI-powered software product.

The Apache 2.0 license grants permission to use, modify, and distribute the source files in this repository. It does not grant permission to use the Tab™ name, branding, or persona identity to market, distribute, or represent a derivative work as "Tab" or as affiliated with the Tab project.

If you fork or modify this project, please choose a different name for your derivative.
