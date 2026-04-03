---
name: bugfix
description: "Focused bugfix session — hand off to the bugfixer agent for pair-programming with the user in real time."
argument-hint: "[project-name]"
---

# Bugfix Session

The user wants a hands-on bugfix session. Set up the context and hand off to the bugfixer agent.

## Protocol

1. **Resolve the project.** If the user passed an argument, match it against `list_projects`. Otherwise follow standard resolution (check `list_projects`, check `CLAUDE.md`, ask if ambiguous).

2. **Load project context.** Call `get_project` for the goal, requirements, and design.

3. **Gather knowledgebase context.** Call `list_documents` for the project. Identify architecture docs, conventions, or prior analysis that might help locate bugs. Collect the document IDs.

4. **Check for relevant tasks.** Call `list_tasks` filtering for `category: "bugfix"` or `status: "todo"` to find known bugs or areas of concern. Collect relevant task IDs.

5. **Spawn the bugfixer in the foreground.** Use `subagent_type: "tab-for-projects:bugfixer"` with `run_in_background: false`. Include in the prompt:
   - The project ID, goal, requirements, and design
   - Knowledgebase document IDs to fetch
   - Any relevant task IDs (known bugs, areas of concern)
   - What the user said about what they want to focus on (if anything)

6. **After the bugfixer completes**, summarize what was accomplished. If the session produced significant insights, offer to spawn the documenter (`subagent_type: "tab-for-projects:documenter"`) to capture findings in the knowledgebase.
