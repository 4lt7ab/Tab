# Tab™

A personal AI assistant defined entirely in markdown. No compiled code, no dependencies, no build system -- just text files that shape how Claude talks, thinks, and works with you.

Tab ships as a **Claude Code plugin**.

---

## Install

Install Tab from the Claude Code plugin marketplace. Tab activates automatically -- no setup commands needed.

### Recommended permissions

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
      "Bash(dd *)",
      "Bash(sudo *)",
      "Bash(su *)",
      "Bash(ssh *)",
      "Bash(scp *)",
      "Bash(sftp *)",
      "Bash(nc *)",
      "Bash(netcat *)",
      "Bash(ncat *)",
      "Bash(socat *)",
      "Bash(git push *)",
      "Bash(git remote add *)",
      "Bash(git remote set-url *)",
      "Bash(npm publish *)",
      "Bash(cargo publish *)",
      "Bash(gem push *)",
      "Bash(twine upload *)",
      "Bash(pip upload *)",
      "Bash(docker push *)",
      "Bash(kubectl *)",
      "Bash(helm *)",
      "Bash(terraform apply *)",
      "Bash(terraform destroy *)",
      "Bash(pulumi *)",
      "Bash(aws *)",
      "Bash(gcloud *)",
      "Bash(az *)",
      "Bash(vercel *)",
      "Bash(netlify *)",
      "Bash(heroku *)",
      "Bash(fly *)",
      "Bash(railway *)",
      "Bash(launchctl *)",
      "Bash(systemctl *)",
      "Bash(crontab *)",
      "Bash(security find-generic-password *)",
      "Bash(security find-internet-password *)"
    ]
  }
}
```

This gives Tab full development capabilities while blocking destructive operations, remote access, package publishing, cloud/deploy CLIs, and credential extraction. Customize to taste.

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

You:  Draw me a scary dinosaur
Tab:  [ASCII art T-Rex with a fun dino fact]
```

---

## Specialists

Tab dispatches specialist sub-agents for autonomous work. They run in the background with isolated context — Tab does the thinking, specialists do the doing.

- **Researcher** — gathers context from codebases, web, and docs. Dispatched when Tab needs information it doesn't have.
- **Implementer** — executes a settled plan in an isolated git worktree. Only dispatched after design questions are resolved and you confirm.
- **Reviewer** — reviews implementation against the plan that produced it. Runs automatically after the implementer finishes.

You can dispatch them explicitly ("have the researcher look into X") or Tab will suggest dispatch when the work is ready for it.

---

## Skills

Tab comes packaged with Skills. Skills activate automatically based on what you say, or you can invoke them directly with slash commands. Built-in behaviors (greeting, status tracking) are part of the agent definition and don't need separate skill files.

### workshop

**Slash command:** `/workshop [idea or problem]`

Sustained collaborative planning. Tab researches the landscape (web search, codebase exploration), lays down a rough plan, then iterates with you in an open loop -- reacting to your feedback, researching before proposing, and updating a living document as decisions land. The session ends when you say it does, and the final doc is restructured so a cold reader could implement from it.

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
  tab.md                # The agent — persona, voice, rules, behaviors, dispatch logic
  researcher.md         # Specialist: gathers context from codebases, web, and docs
  implementer.md        # Specialist: executes settled plans in isolated worktrees
  reviewer.md           # Specialist: reviews implementation against the plan
skills/
  workshop/SKILL.md     # Collaborative idea workshopping and planning
  draw-dino/SKILL.md    # ASCII art dinosaurs
.claude-plugin/
  plugin.json           # Plugin manifest
settings.json           # Activates Tab as the primary persona
```

### How It Works

**`agents/tab.md`** is the agent definition. Its YAML frontmatter declares identity and memory scope. The body defines voice, rules, behaviors, and dispatch logic for specialists. Skills are discovered automatically from the `skills/` directory — they don't need to be listed in the agent frontmatter.

**Specialist agents** (`researcher.md`, `implementer.md`, `reviewer.md`) are sub-agents Tab dispatches for autonomous work. Each runs in background with a fresh context — the dispatch brief is their entire world. They're registered in `plugin.json` and available as `subagent_type: "tab:<Name>"`.

**`settings.json`** at the plugin root sets `"agent": "tab:Tab"`, which tells Claude Code to load Tab as the primary persona. This is the mechanism that makes Tab "just work" after install -- no setup commands needed. Note: plugin `settings.json` only supports the `agent` key. Permissions are configured in the user's project-level `.claude/settings.json` (see [Recommended permissions](#recommended-permissions)).


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

Skills that produce artifacts write them wherever makes sense for the project.

### Add a New Skill

1. **Create the directory:** `skills/my-skill/SKILL.md`

2. **Write frontmatter** with `name`, `description` (as trigger condition), and optionally `argument-hint`.

3. **Write the body.** Define workflow, instructions, constraints. Start with a "What This Skill Does" section.

4. **That's it.** Claude Code discovers skills automatically from the `skills/` path declared in `plugin.json`. No registration needed.

5. **If it needs scripts or assets**, put them alongside `SKILL.md` in the skill directory.

### Conventions

- **Naming:** lowercase, hyphenated directories and files.
- **Git commits:** conventional prefixes -- `feat:`, `fix:`, `docs:`, `refactor:`, `chore:`.
- **Output:** skills write artifacts wherever makes sense for the project — no fixed output directory.
- **No code:** this project has no tests, no linting, no build. If you're writing code, you're in the wrong repo.

---

## Trademark

Tab™ is a trademark of Jacob Fjermestad (AltT4b), used to identify the Tab AI persona, agent, and associated personality definition files. This trademark applies specifically to the use of "Tab" as the name of an AI assistant, AI agent, AI persona, or AI-powered software product.

The Apache 2.0 license grants permission to use, modify, and distribute the source files in this repository. It does not grant permission to use the Tab™ name, branding, or persona identity to market, distribute, or represent a derivative work as "Tab" or as affiliated with the Tab project.

If you fork or modify this project, please choose a different name for your derivative.
