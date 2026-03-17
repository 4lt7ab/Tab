# Tab™

A thinking partner defined entirely in markdown. No compiled code, no dependencies, no build system — just text files that shape how Claude talks, thinks, and works with you.

Tab ships as a **Claude Code plugin**.

---

## Install

**From the marketplace:** Search for "Tab" in the Claude Code plugin marketplace and install it. Tab activates automatically — no setup commands needed.

**From a local clone:** Clone this repo, then add it as a plugin in Claude Code by pointing at the directory. Claude Code discovers the plugin via `.claude-plugin/plugin.json`, which registers Tab's agents and auto-discovers skills from `skills/`. The included `settings.json` sets Tab as the primary persona automatically.

For the full Claude Code plugin install workflow, see the [Claude Code documentation](https://docs.anthropic.com/en/docs/claude-code). To verify the install, ask Tab something — if it responds in character, you're set.

### Permissions

Tab works out of the box with default Claude Code permissions — you'll be prompted for each tool use. Customize your project's `.claude/settings.json` to taste as you learn which prompts you want to skip and which you want to keep.

---

## Quick Start

Talk to Tab like a person. No special syntax needed. Tab picks up on intent and activates the right skill.

```
You:  Hey Tab
Tab:  [responds in character, orients you on what's happening]

You:  Let's workshop a notification system
Tab:  [researches the landscape, lays out a rough plan, iterates with you until it's solid]

You:  Send it to the implementer
Tab:  [dispatches the plan to a specialist in an isolated worktree]
      ...
Tab:  [implementer finishes — Tab automatically dispatches a reviewer, then surfaces the results]
```

---

## Specialists

Tab dispatches specialist sub-agents for autonomous work. They run in the background with isolated context — Tab does the thinking, specialists do the doing.

- **Researcher** — gathers context from codebases, web, and docs. Dispatched when Tab needs information it doesn't have.
- **Implementer** — executes a settled plan in an isolated git worktree. Only dispatched after design questions are resolved and you confirm. When it finishes, Tab will tell you where the worktree is and nudge you to review the diff and merge it — nothing lands in your working branch until you do.
- **Reviewer** — reviews implementation against the plan that produced it. Runs automatically after the implementer finishes. Reports back to Tab, who surfaces what matters.

You can dispatch them explicitly ("have the researcher look into X", "research this") or Tab will suggest dispatch when the work is ready for it.

### Merging a Worktree

After the implementer finishes and Tab reports the results, the work lives in an isolated git worktree. To bring it into your working branch: review the diff (`git diff main...worktree-branch`), merge it (`git merge worktree-branch`), and clean up the worktree (`git worktree remove <path>`). Tab will tell you the branch name and worktree path when the work is done.

---

## Skills

Skills activate automatically based on what you say, or you can invoke them directly with slash commands.

### workshop

**Slash command:** `/workshop [idea or problem]`

Sustained collaborative planning. Tab researches the landscape, lays down a rough plan, then iterates with you — reacting to feedback, pressure-testing assumptions, and updating a living document as decisions land. The workshop is done when all open questions are resolved.

Plans are saved to `.tab/<topic>.md` in your project directory. If you start a workshop on the same topic in a future session, Tab will find the file and pick up where you left off. Commit `.tab/` if you want plans in version control; add it to `.gitignore` if you'd rather keep them local.

### log

**Slash command:** `/log [what to log]`

Deferred work tracking. When something surfaces that doesn't need doing right now — out-of-scope issues, "we'll handle that later" items, known gaps from a workshop or review — Tab logs it to `docs/maintenance/` so the team has a shared record of what's waiting. One file per item, named descriptively. Tab also surfaces this proactively when deferred work comes up in conversation.

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
