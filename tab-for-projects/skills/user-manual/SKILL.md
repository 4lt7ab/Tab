---
name: user-manual
description: "Quickstart guide to tab-for-projects — what it is, how skills and the Developer agent work, and how to make the most of it. Use when the user is new, asks how tab-for-projects works, or invokes /user-manual."
---

# Tab for Projects — User Manual

A quickstart guide to the tab-for-projects plugin. Run `/user-manual` anytime you want a refresher on what's available and how to use it.

## Trigger

**When to activate:**
- The user runs `/user-manual`
- The user asks how tab-for-projects works, what agents are available, or how to get started
- The user seems unsure what the plugin can do for them

**When NOT to activate:**
- The user is already working productively — don't interrupt with a tutorial
- The user asks about the standalone Tab agent — that's a different plugin entirely

## What Is Tab for Projects?

Tab for Projects gives your conversational agent a persistent memory layer and a specialist builder. The memory layer is the Tab for Projects MCP — projects, tasks, and KB documents that survive between sessions. The builder is the Developer agent, dispatched in worktrees when code needs to be written.

You bring your own agent. The plugin tells it how to work with structure.

**What it adds to your workflow:**
- **Persistence.** Projects, tasks, and documents survive between sessions. Pick up where you left off.
- **Structure.** Ideas turn into projects with goals, requirements, and design. Work turns into tasks with plans, acceptance criteria, and dependency chains. Knowledge turns into a curated knowledgebase.
- **A real builder.** The Developer agent owns the codebase — claims tasks, gathers context, implements, tests, commits, and merges. It works in worktrees so your working tree stays clean.

## The Developer Agent

The only subagent. Owns the codebase. Gets dispatched by your conversational agent (via skills like `/build` and `/investigate`) to do focused implementation or analysis work.

**What it does:**
- Claims tasks and implements them, following conventions and KB documentation
- Writes and maintains CLAUDE.md files (the codebase's own documentation layer)
- Analyzes code when your agent needs codebase understanding
- Runs tests, commits changes, merges worktree branches, and reports what happened

**It has a real process.** For implementation: claim tasks, gather context (task plans, KB docs, codebase patterns), implement with ceremony scaled to effort, test, update CLAUDE.md, commit, merge, report. For analysis: read the code, understand the patterns, check documentation coverage, return a structured report.

**It stays in its lane.** The Developer reads KB documents for context but never creates or updates them. It notes follow-up work in reports but never creates tasks. Your conversational agent handles project structure, KB curation, and task management — the Developer handles code.

## Skills — The Interface

Skills are the interface between you and the plugin. Each one handles a different ceremony level, from casual check-ins to full project creation. Your conversational agent activates them based on slash commands or conversational triggers.

| Command | What it does | When to reach for it |
|---------|-------------|---------------------|
| `/kickoff` | Takes an idea and stands up a full project — goal, requirements, design, KB docs, and tasks. Interactive discovery, inline creation. | You're starting something new. |
| `/plan` | Designs a feature and decomposes it into implementation tasks within an existing project. | You know what to build next but need it broken into pieces. |
| `/build` | Execution loop — picks up ready tasks, dispatches the Developer in worktrees, handles blockers inline, captures knowledge as it goes. | You want code written. The big one. |
| `/status` | Quick health brief — what's ready, blocked, stale, and progressing. | You want to know where things stand. |
| `/review` | Retrospective — compares what was built against what was planned, audits KB accuracy. | A batch of work just landed and you want an honest look-back. |
| `/maintain` | Housekeeping sweep — cleans up task shape, curates the KB, freshens in-code docs. | Things feel messy or it's been a while since anyone tidied up. |
| `/investigate` | Dispatches the Developer to analyze code. Persists findings as KB documentation. | You want to understand how something works *and* remember it next session. |
| `/user-manual` | This guide. | You're new, or it's been a while. |

## How It Fits Together

A typical flow for a new feature:

1. **You** describe what you want to build
2. **Your agent** (via `/kickoff`) captures it as a project with goals, requirements, design, and tasks
3. **Your agent** (via `/plan`) refines features into implementation-ready tasks with plans and acceptance criteria
4. **Your agent** (via `/build`) dispatches the Developer to implement ready tasks in worktrees
5. **Your agent** (via `/status`) checks progress — what's done, what's blocked, what's next
6. **Your agent** captures new patterns and decisions in the KB along the way

You don't have to follow this linearly. Jump in wherever makes sense. Run `/build` if tasks are already defined. Run `/investigate` if you need to understand code before planning. Run `/status` if you just want to know where things stand.

## Creative Ways to Use It

**As a memory layer.** Even if you're doing all the coding yourself, use the project structure to track what you're working on and the KB to document decisions. Next session, everything's still there. Your agent doesn't start from scratch.

**As a design partner.** Use `/kickoff` and `/plan` to think through features before building. Writing goals, requirements, and task plans catches problems earlier than jumping straight to code.

**As a documentation system.** Run `/investigate` against parts of your codebase and let the findings accumulate in the KB. Architecture, patterns, conventions — all persistent, all available to your agent next session. Useful for onboarding, consistency, and not losing institutional knowledge.

**As a full dev workflow.** Describe a feature, kick it off, plan the tasks, build them. Review the output, iterate, repeat. The Developer handles implementation in worktrees while you stay focused on direction.

**As a backlog janitor.** Run `/maintain` to sweep through task health. Stale tasks? Vague descriptions? Missing acceptance criteria? Tangled dependencies? It finds them and fixes what it can.

## Tips

- **Projects persist.** Everything you create lives in the MCP. Come back tomorrow, next week, next month — it's all there.
- **Tasks have a lifecycle.** `todo` -> `in_progress` -> `done`. The Developer claims tasks, implements them, and marks them done. Your agent watches the flow.
- **Documents are reusable.** A convention doc or architecture overview can link to multiple projects. Write it once, reference it everywhere.
- **You're the boss.** Your agent and the Developer suggest, organize, and build — but you decide what matters, what's in scope, and when to ship. They won't pressure you toward execution if you're still thinking.
