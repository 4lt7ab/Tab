# Skills

Skills are slash-command capabilities in the Claude Code plugin system. They are lighter than agents -- each skill is defined in a `SKILL.md` file and activated by typing its command in the chat. Skills give Tab (and its packages) specific, repeatable behaviors that users can invoke on demand.

A skill's `SKILL.md` declares its name, a description used for matching, and an argument hint showing what parameters it accepts. When a user types the corresponding slash command, Tab follows the instructions in that file.

---

## draw-dino

**Package:** tab
**Invocation:** `/draw-dino [species]`

Draws ASCII art dinosaurs. If the user names a specific species, Tab draws that one. If not, Tab picks one itself.

### How it works

1. Note the requested species or customization. If none is given, choose a classic dinosaur.
2. Freestyle draw the dinosaur as ASCII art inside a code block (so spacing is preserved).
3. After drawing, include a short fun fact related to the species.

### Customization

The species and style adapt to the user's request:

- **Cute / baby** -- draws a Baby Dino
- **Flying** -- draws a Pterodactyl
- **Scary / fierce** -- draws a T-Rex or Velociraptor
- **Big / gentle** -- draws a Brontosaurus

### Design principles

- Low stakes on purpose. The skill exists to be fun and lower the barrier to interaction.
- Always deliver. No clarifying questions, no refusals. Pick a dino and draw it.
- Personality over precision. A charming dinosaur with wobbly legs beats a technically perfect one with no character.

---

## listen

**Package:** tab
**Invocation:** `/listen [optional topic]`

A deliberate listening mode. Tab goes silent while the user thinks out loud -- dumping ideas, working through confusion, venting, brainstorming. When the user signals they are done, Tab synthesizes what it heard and hands back the structure that was hiding in the stream.

### Entering listen mode

When the user runs `/listen`:

1. Tab acknowledges with a single short line, something like: *"Listening. Say 'done' when you're ready for the synthesis."*
2. If a topic was passed (e.g. `/listen auth redesign`), Tab notes it internally as context but does not comment on it.
3. Tab goes silent.

### While listening

- **Say nothing.** No reactions, no clarifications, no encouragement, no emoji, no questions. Absolute silence.
- **Track everything.** Themes, contradictions, emotional weight, decisions made mid-thought, questions the user asked themselves, things they repeated (repetition signals importance).
- **Note what is unsaid.** If the user talks around something without naming it, that is signal too.

The only exception: if the user directly asks Tab a question (genuinely addressed to Tab, not rhetorical), Tab answers briefly and returns to silence.

### Ending listen mode

The user ends it by saying something like "done," "finished," "that's it," or any clear signal they are handing the floor back. If genuinely ambiguous whether they want synthesis or are just shifting topics, Tab asks.

### The synthesis

This is where Tab earns the silence. The synthesis covers:

1. **Structure.** Organize what the user said into coherent themes or threads. Show them the shape of their own thinking.
2. **Contradictions.** If the user said A early on and not-A later, name it without judgment.
3. **Energy.** What did they spend the most time on? What did they repeat? What made them change direction? That is where the real priority lives.
4. **Gaps.** If there is an obvious missing piece that their plan depends on, flag it.
5. **Mirror first, opinions second.** The synthesis reflects the user's thinking faithfully. If Tab has a strong reaction, it comes after the synthesis, clearly separated.

The synthesis is not a transcript, not a to-do list (unless the user was clearly listing tasks), and not advice. It is the user's thinking, organized.

After the synthesis, Tab returns to normal mode. The listening context stays available for the rest of the session.

---

## refinement

**Package:** tab-for-projects
**Invocation:** `/refinement [project-name]`

An interactive backlog refinement ceremony. Tab acts as a facilitator, walking through the project's active tasks with the user to make sure every task is understood, scoped, and actionable before implementation begins.

### Starting the session

1. **Resolve the project.** If the user provided an argument, match it against the project list. Otherwise follow the standard project resolution flow.
2. **Load project context.** Pull the goal, requirements, and design so Tab can evaluate whether tasks align with the project's intent.
3. **List the active backlog.** Filter for tasks with status `todo` or `in_progress`.
4. **Present the session overview:**
   - Project name and goal (one line)
   - Number of tasks in the backlog
   - A scannable list showing each task's title, effort, impact, category, and whether it has a plan
   - Call out tasks that look under-specified (no description, no plan, no effort estimate)

Then ask the user how they want to proceed -- walk through everything in order, focus on a specific group, or start with the tasks that need the most attention.

### Per-task refinement loop

For each task the user wants to refine:

1. **Present the task.** Show title, description, effort/impact estimates, category, group, plan, acceptance criteria, and what is missing or unclear.
2. **Discuss and research.** Work through the task with the user:
   - Clarify intent -- does the description capture *why* the task exists?
   - Validate scope -- is this one task or three?
   - Identify unknowns -- if the task touches unfamiliar parts of the codebase, spawn a background research agent to investigate rather than guessing.
   - Check assumptions -- verify that assumptions about the current state of the code are actually true.
   - Estimate effort -- discuss and calibrate using research findings.
   - Define "done" -- capture acceptance criteria if the user has opinions about what done looks like.
3. **Update the task.** Persist refined description, updated estimates, acceptance criteria, and notes immediately via the MCP. Updates happen as you go so nothing is lost if the session is interrupted.

### What a refined task looks like

- A description that someone with zero context would understand next week
- An effort estimate grounded in codebase research, not vibes
- Acceptance criteria that make "done" unambiguous (when the user has opinions)
- Enough understanding that planning would be straightforward
- No hidden unknowns -- uncertainty is flagged, not ignored

### Session flow

The session is conversational, not mechanical. Tab follows the user's energy:

- If they want to dive deep on one task, dive deep.
- If they want to skim and flag tasks that need work, skim.
- If they realize the backlog is missing something, help capture it.
- If they want to reorganize, regroup, or reprioritize, do it.

### Ending the session

When the user is done or the backlog is fully refined, Tab:

1. Summarizes what changed -- how many tasks were refined, what was added, what is still pending.
2. Calls out tasks that still need attention (under-specified, waiting on research, blocked).
3. Notes any background agents still running.
4. Optionally spawns a QA agent to check for missing work across the refined backlog, if the user wants it.

---

## bugfix

**Package:** tab-for-projects
**Invocation:** `/bugfix [project-name]`

A focused bugfix session. The manager sets up project context and hands off to the bugfixer agent, which runs in the foreground and pair-programs with the user to hunt and fix bugs in real time.

### How it works

1. **Resolve the project.** Match the argument against the project list, or follow the standard resolution flow.
2. **Load project context.** Fetch the project's goal, requirements, and design.
3. **Gather knowledgebase context.** List the project's documents and identify architecture docs, conventions, or prior analysis that might help locate bugs.
4. **Check for relevant tasks.** Look for tasks with `category: "bugfix"` or `status: "todo"` to find known bugs or areas of concern.
5. **Spawn the bugfixer in the foreground.** The bugfixer agent (`tab-for-projects:bugfixer`) takes over the conversation with `run_in_background: false`. It receives the project ID, knowledgebase document IDs, relevant task IDs, and the user's focus area.
6. **After the session.** The manager summarizes what was accomplished and offers to spawn the documenter to capture findings in the knowledgebase.

### Design principles

- The bugfixer is the only subagent that runs in the foreground and talks directly to the user. This is intentional -- bug hunting is collaborative and conversational.
- The find-fix-verify loop is tight: find a bug, fix it immediately, verify with a test, move on. Bugs that are too large for the session get tracked as MCP tasks.
- Every fix gets a test. A bug without a test is a bug that comes back.
- The `.local/` directory accumulates reusable tools (test runners, repro scripts, coverage helpers) across sessions.

---

## autopilot

**Package:** tab-for-projects
**Invocation:** `/autopilot [project-name]`

Autonomous project coordination. The system assesses the project, identifies what needs doing, and does it -- without asking for permission at each step. The user can type `/autopilot`, walk away, and come back to a project that has been triaged, planned, implemented, validated, and documented.

### How it works

1. **Resolve the project** and load full context (goal, requirements, design, knowledgebase documents).
2. **Phase 1 -- Assessment.** Spawn the coordinator in coordinate mode with full project scope. The coordinator reads the entire project state, takes direct MCP actions (fixing statuses, archiving duplicates, creating tasks for gaps), and returns structured dispatch instructions identifying which tasks need planning, QA, documentation, and implementation.
3. **Phase 2 -- Dispatch.** Based on the coordinator's dispatch instructions, spawn planner, QA, and documenter agents in parallel -- each with the specific task IDs and context from the coordinator's findings. Only agents with work to do are spawned.
4. **Phase 3 -- Implementation.** After Phase 2 completes, identify tasks ready for implementation (from the coordinator's `implement` dispatch array and newly-planned tasks). Group them into dependency-ordered waves, respecting file conflicts. Spawn implementer agents in parallel within each wave (capped at 3--5 concurrent agents). Wait for each wave to complete before starting the next.
5. **Phase 4 -- Post-implementation QA.** Validate the newly implemented work by spawning QA on all tasks that implementers completed. Failures are reported but not automatically retried -- the autopilot is autonomous but bounded.
6. **Results.** Present a full summary: what the coordinator assessed and acted on, what the planner produced, what QA found (both pre-existing and post-implementation), what the documenter captured, what was implemented (successes, failures, skips), and items that need the user's judgment.

### Design principles

- Autopilot is a permission structure. Without it, the manager asks before acting. Autopilot says: "Go."
- The multi-phase design makes the manager a team lead: the coordinator is the analyst, the planner/QA/documenter/implementer are the specialists. The coordinator does not spawn agents itself -- it returns instructions, and the manager dispatches.
- Implementation runs in waves to respect dependencies and avoid file conflicts between concurrent implementers.
- No retry loops. If implementation or QA fails, it is reported and left for the user to address.
