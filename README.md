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

### draft

**Slash command:** `/draft [source material]`

Translates decided plans into reviewable proposed-changes docs. Takes a workshop plan, brain dump, or settled idea and produces an ordered set of exact file edits with inline rationale. Iterative by design -- propose, review, refine. Output goes to `.tab/work/<topic>/draft-<concern>.md`.

### feedback

**Slash command:** `/feedback [artifact or idea]`

Structured, graded (A-F) feedback on code, prose, plans, or ideas. Leads with a letter grade, skips nitpicks, groups feedback by importance.

### template

**Slash command:** `/template [type of work]`

Guided interview that produces reusable reference docs for recurring types of work. Researches prior art first, then asks only what it couldn't infer. Output goes to `.tab/work/<topic>/template-<pattern>.md`.

### draw-dino

**Slash command:** `/draw-dino [species]`

ASCII art dinosaurs. Customizable by mood: cute/baby, flying (pterodactyl), scary/fierce (T-Rex), big/gentle (brontosaurus). Includes a fun fact with each drawing.

### Built-in: Greeting

Tab greets and orients on session start. First-time users get a short intro; returning users get relevant context from status and recent work.

### Built-in: Status Tracking

Tab maintains `.tab/status.md` automatically — a lightweight orientation file that tracks what's in progress and what recently shipped. No manual memory commands needed. All skill output lives under `.tab/work/<topic>/` — an unfinished workshop doc is an open thread, a draft not yet executed is pending work.

---

## For Contributors

### Project Layout

```
agents/
  tab.md                # Claude Code agent (persona, voice, rules, skills via frontmatter)
skills/
  workshop/SKILL.md     # Collaborative idea workshopping and planning
  draft/SKILL.md        # Translates settled plans into proposed-changes docs
  feedback/SKILL.md     # Structured, graded feedback
  template/SKILL.md     # Guided interview for reusable reference docs
  draw-dino/SKILL.md    # ASCII art dinosaurs
.claude-plugin/
  plugin.json           # Plugin manifest
settings.json           # Activates Tab as the primary persona
```

### How Agents Work

**`agents/tab.md`** is the Claude Code agent. Its YAML frontmatter declares identity and lists skills (`tab:feedback`, `tab:workshop`, `tab:draft`, `tab:template`, `tab:draw-dino`). The body defines voice, rules, status tracking behavior, and a table mapping each skill to its output directory under `.tab/work/`.

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

Skills that produce file output write to `.tab/work/<topic>/`. Skills reference `<output-dir>` in their instructions rather than hardcoding paths.

### Add a New Skill

1. **Create the directory:** `skills/my-skill/SKILL.md`

2. **Write frontmatter** with `name`, `description` (as trigger condition), and optionally `argument-hint`.

3. **Write the body.** Define workflow, instructions, constraints. Start with a "What This Skill Does" section.

4. **Register in the agent.** Add `tab:my-skill` to the `skills:` list in `agents/tab.md` frontmatter. If the skill produces file output, add a row to the skill table in the agent body. (You don't need to touch `plugin.json` -- Claude Code discovers skills automatically from the `skills/` path.)

5. **If it needs scripts or assets**, put them alongside `SKILL.md` in the skill directory.

### Status Tracking

Tab maintains `.tab/status.md` automatically as operational bookkeeping — no user approval needed. The file tracks in-progress work (active workshops, pending drafts) and recent completions. Tab updates it at session boundaries and when work state changes. See the Status section in `agents/tab.md` for the full spec.

### Conventions

- **Naming:** lowercase, hyphenated directories and files.
- **Git commits:** conventional prefixes -- `feat:`, `fix:`, `docs:`, `refactor:`, `chore:`.
- **Output:** all skill output goes to `.tab/work/<topic>/` in the user's working directory, which is gitignored.
- **No code:** this project has no tests, no linting, no build. If you're writing code, you're in the wrong repo.

---

## Trademark

Tab™ is a trademark of Jacob Fjermestad (AltT4b), used to identify the Tab AI persona, agent, and associated personality definition files. This trademark applies specifically to the use of "Tab" as the name of an AI assistant, AI agent, AI persona, or AI-powered software product.

The Apache 2.0 license grants permission to use, modify, and distribute the source files in this repository. It does not grant permission to use the Tab™ name, branding, or persona identity to market, distribute, or represent a derivative work as "Tab" or as affiliated with the Tab project.

If you fork or modify this project, please choose a different name for your derivative.
