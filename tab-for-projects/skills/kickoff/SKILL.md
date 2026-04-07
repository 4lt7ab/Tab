---
name: kickoff
description: "Take an idea and stand up a fully-formed project ready to build."
argument-hint: "<idea description or path to IDEA.md>"
mode: conversational
agents:
  - tab-for-projects:project-manager
  - tab-for-projects:tech-lead
requires-mcp:
  - tab-for-projects
---

# Kickoff — New Project Ceremony

The starting play. Takes a raw idea — maybe a sentence, maybe an IDEA.md — and turns it into a fully-formed project with goals, requirements, design, documentation, and implementation tasks. This is the only conversational skill because starting a project deserves a ceremony: discovery, refinement, and grounding in existing knowledge before any agent touches anything.

## Trigger

**When to activate:**
- The user runs `/kickoff`
- The user says "start a new project" or "I want to build [thing]" and no project exists for it yet

**When NOT to activate:**
- The user wants to add a feature to an existing project (that's `/plan`)
- The user wants to build existing tasks (that's `/build`)
- A project already exists for the idea — suggest `/plan` or `/status` instead

## Arguments

- **Free-text idea:** "A CLI tool that turns markdown into slide decks"
- **Path to IDEA.md:** A file from `/think` or manually written. Tab reads it and uses its content as the seed.
- **No argument:** Tab asks what they want to build. One open question, not a form.

## Sequence

### Phase 1: Discovery (Interactive)

1. **Search the existing KB** for context that might inform the new project:
   ```
   list_documents({ search: "<topic keywords>" })
   list_documents({ tag: "architecture" })
   list_documents({ tag: "conventions" })
   ```

   Look for: relevant architecture docs, convention docs, pattern records, prior design decisions. Existing knowledge is the foundation — don't design in a vacuum when patterns already exist.

2. **Reflect back and refine with the user.** This is the ceremony.

   Start from the seed (argument, IDEA.md, or the user's first answer). Reflect back what you understood. Surface any relevant KB context: "There's an existing convention doc about [X] that would apply here" or "The architecture for [Y] is already documented — we can build on that."

   Draw out the pieces needed for a well-formed project:
   - **Goal:** What is this thing and why does it matter?
   - **Requirements:** What must it do? Concrete capabilities and constraints.
   - **Design:** How should it work? Architecture, technical approach, key decisions.

   Follow the user's energy. If they have strong opinions about the design, go deep there. If they just want to describe the behavior, let the Tech Lead figure out the how. Three to five exchanges is usually enough. Don't over-interview.

   **When to stop:** The goal is clear, requirements are concrete enough to scope tasks from, and design has enough direction for the Tech Lead. When you start circling, summarize what you've got and ask if they want to add anything.

### Phase 2: Agent Dispatch (Autonomous)

3. **Dispatch Project Manager** to create the project:
   - Provide: title, goal, requirements, design — all refined during the interactive session
   - The PM creates the project and returns the project ID

4. **Dispatch Tech Lead** (first pass — initial documentation) with:
   - `project_id`: the newly created project ID
   - `dispatch_type`: `write`
   - `scope`: "initial architecture and design documentation"
   - `context`: the project goal, requirements, design, and any relevant existing KB documents identified in Phase 1

   The TL writes foundational KB documents — architecture overview, key design decisions, conventions if applicable. It attaches them to the project.

5. **Dispatch Tech Lead** (second pass — task decomposition) with:
   - `project_id`: the project ID
   - `dispatch_type`: `write`
   - `scope`: "task decomposition"
   - `context`: the project fields, the design doc just created, and the instruction to decompose the full project scope into implementation tasks with descriptions, plans, acceptance criteria, effort/impact, dependencies, and group keys

   The TL produces a decomposition that Tab routes to the PM.

6. **Dispatch Project Manager** with:
   - `project_id`: the project ID
   - `focus`: `task-shape`
   - Context: the Tech Lead's decomposition

   The PM creates tasks, wires dependencies, calibrates estimates, and health-checks everything.

### Phase 3: Handoff

7. **Read all reports.** Compile the full picture.

## Output

Present the project summary:

**Project created** — Title, goal (one sentence), and link/ID.

**Design** — Key design decisions and approach. Reference the architecture doc for full details.

**KB seeded** — Documents created, with titles and types.

**Task breakdown** — Table of tasks with titles, effort, impact, and group. Ordered by dependency.

**Ready to build** — Which tasks are unblocked and can start immediately.

**Open items** — Anything flagged for human decision, or design questions that were explicitly deferred during the ceremony.

Close with a brief note that the project is ready — suggest `/build` to start implementation or `/status` for a health check.

## Edge Cases

- **IDEA.md is comprehensive:** If the user provides a thorough IDEA.md, the interactive phase can be brief — confirm the key points and move to dispatch. Don't re-interview what's already well-articulated.
- **IDEA.md is thin:** Treat it as a seed, same as a free-text argument. The interactive phase fills the gaps.
- **Existing project covers the same idea:** If the KB search or project list reveals an existing project, surface it. Ask whether to proceed with a new project or work within the existing one (which would be a `/plan` instead).
- **User wants to skip the ceremony:** Respect it. If they say "just create it," take what they've given you and move straight to agent dispatch. The ceremony is valuable, not mandatory.
