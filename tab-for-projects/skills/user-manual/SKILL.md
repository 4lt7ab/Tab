---
name: user-manual
description: "Quickstart guide to tab-for-projects — what it is, how the agents work together, and how to make the most of it. Use when the user is new, asks how tab-for-projects works, or invokes /user-manual."
---

# Tab for Projects — User Manual

A quickstart guide to the tab-for-projects plugin. Run `/user-manual` anytime you want a refresher on what's available and how to use it.

## Trigger

**When to activate:**
- The user runs `/user-manual`
- The user asks how tab-for-projects works, what agents are available, or how to get started
- The user seems unsure what the plugin can do for them

**When NOT to activate:**
- The user is already working productively with an agent — don't interrupt with a tutorial
- The user asks about the standalone Tab agent — that's a different plugin entirely

## What Is Tab for Projects?

Tab for Projects is a team of three AI agents that help you plan, track, and build software projects. They share a persistent memory layer (the Tab for Projects MCP) where your projects, tasks, and documentation live across sessions.

Think of it as a tiny engineering org that remembers everything. You describe what you want to build. The agents help you organize it, document it, and build it — and they remember where you left off next time.

**What makes it different from just talking to Claude:**
- **Persistence.** Projects, tasks, and documents survive between sessions. Pick up where you left off.
- **Specialization.** Three agents with distinct roles, not one generalist trying to do everything.
- **Structure.** Ideas turn into projects with goals, requirements, and design. Work turns into tasks with plans, acceptance criteria, and dependency chains. Knowledge turns into a curated knowledgebase.

## The Agents

### Project Manager

**The organizer.** Obsessed with project health — making sure goals are clear, tasks are well-formed, dependencies make sense, and progress is real.

**What they do:**
- Capture your ideas as structured projects with goals, requirements, and design
- Break work into tasks with descriptions, plans, and acceptance criteria
- Track progress — what's done, what's blocked, what's stale
- Keep the project honest — flag vague requirements, missing plans, stale statuses

**When to use them:**
- You have an idea and want to organize it into actionable work
- You want to check in on a project — what's done, what's next, what's stuck
- You want help thinking through requirements or scoping work
- You want someone to wrangle a messy backlog into shape

**Good first moves:**
- "I want to build [thing]. Help me organize it."
- "What's the status of my project?"
- "These tasks feel too big — help me break them down."

### Tech Lead

**The documentarian.** Owns the knowledgebase — every design doc, architecture decision, convention record, and pattern reference.

**What they do:**
- Write and maintain design documents, ADRs, convention docs, and architecture overviews
- Investigate the codebase (via the developer) to keep documentation accurate
- Decompose large features into well-documented tasks
- Curate the knowledgebase — merge duplicates, prune stale docs, keep it lean

**When to use them:**
- You want to document an architectural decision or design
- You need a feature broken down into implementation tasks with full context
- You want the knowledgebase audited — is it accurate? Are there gaps?
- You want a design doc written before diving into implementation

**Good first moves:**
- "Document our API architecture."
- "Break down [feature] into tasks."
- "Audit the knowledgebase — what's stale, what's missing?"

### Developer

**The builder.** Owns the codebase — implements features, fixes bugs, maintains in-code documentation, and can analyze any part of the code.

**What they do:**
- Pick up tasks and implement them, following conventions and KB documentation
- Write and maintain CLAUDE.md files (the codebase's own documentation layer)
- Analyze code when other agents need codebase understanding
- Run tests, commit changes, and record what was done

**When to use them:**
- You have a well-defined task ready for implementation
- You want code analyzed — "how does [subsystem] work?"
- You want CLAUDE.md files created or updated for a module
- You want a bug investigated and fixed

**Good first moves:**
- "Pick up the next ready task and implement it."
- "How does [module] work? Walk me through it."
- "Fix the bug described in [task]."

## How They Work Together

The agents have clear ownership boundaries:

| Domain | Owner |
|--------|-------|
| Project fields and task shape | Project Manager |
| Knowledgebase documents | Tech Lead |
| Codebase and in-code docs | Developer |

A typical flow for a new feature:

1. **You** describe what you want to build
2. **Project Manager** captures it as a project with goals and requirements
3. **Tech Lead** writes a design doc and decomposes the work into tasks
4. **Developer** picks up ready tasks and implements them
5. **Project Manager** tracks progress and flags issues
6. **Tech Lead** captures new patterns and decisions in the knowledgebase

You don't have to follow this linearly. Jump in wherever makes sense. Start with the developer if you just want code written. Start with the tech lead if you need a design first. Start with the project manager if you want to organize your thinking.

## Skills — Your Slash Commands

Skills are workflows that orchestrate the agents for you. Instead of talking to each agent individually, you run a slash command and the right agents get dispatched in the right order.

| Command | What it does | When to reach for it |
|---------|-------------|---------------------|
| `/kickoff` | Takes an idea and stands up a full project — goal, requirements, design, KB docs, and tasks. | You're starting something new. |
| `/plan` | Designs a feature and decomposes it into implementation tasks within an existing project. | You know what to build next but need it broken into pieces. |
| `/build` | Picks up ready tasks and implements them. Handles blockers, captures knowledge as it goes. | You want code written. The big one. |
| `/status` | Quick health brief — what's ready, blocked, stale, and progressing. | You want to know where things stand. |
| `/review` | Retrospective — compares what was built against what was planned, audits KB accuracy. | A batch of work just landed and you want an honest look-back. |
| `/maintain` | Housekeeping sweep — cleans up task shape, curates the KB, freshens in-code docs. | Things feel messy or it's been a while since anyone tidied up. |
| `/investigate` | Analyzes code and persists the findings as KB documentation. | You want to understand how something works *and* remember it next session. |

You can also run `/user-manual` anytime to pull up this guide again.

## Creative Ways to Use It

**As a memory layer.** Even if you're doing all the coding yourself, use the project manager to track what you're working on and the tech lead to document decisions. Next session, everything's still there.

**As a design partner.** Use the tech lead to write design docs and ADRs before you build. Thinking on paper (or in a knowledgebase) catches problems earlier than thinking in code.

**As a documentation team.** Point the tech lead at your codebase and let it build a knowledgebase of patterns, conventions, and architecture. Useful for onboarding, consistency, and not losing institutional knowledge.

**As a full dev team.** Describe a feature, let the project manager scope it, the tech lead design it, and the developer build it. Review the output, iterate, repeat.

**As a backlog janitor.** Have the project manager audit your project health. Stale tasks? Vague descriptions? Missing acceptance criteria? Tangled dependencies? It'll find them and fix what it can.

## Tips

- **Projects persist.** Everything you create lives in the MCP. Come back tomorrow, next week, next month — it's all there.
- **Tasks have a lifecycle.** `todo` → `in_progress` → `done`. The developer claims tasks, implements them, and marks them done. The project manager watches the flow.
- **Documents are reusable.** A convention doc or architecture overview can link to multiple projects. Write it once, reference it everywhere.
- **You're the boss.** The agents suggest, organize, and build — but you decide what matters, what's in scope, and when to ship. They won't pressure you toward execution if you're still thinking.
