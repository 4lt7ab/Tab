# Agent Teams

> **Source:** [code.claude.com/docs/en/agent-teams.md](https://code.claude.com/docs/en/agent-teams.md)
>
> **Status:** Experimental -- disabled by default. Requires `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` set to `1` in environment or `settings.json`.
>
> **Minimum version:** Claude Code v2.1.32+

Agent teams coordinate multiple Claude Code instances working together. One session acts as the **team lead** (creates the team, spawns teammates, synthesizes results). **Teammates** are independent Claude Code sessions with their own context windows. Unlike subagents, teammates can message each other directly and self-coordinate through a shared task list.

---

## When to Use Agent Teams (vs Subagents)

|                   | Subagents                                        | Agent teams                                         |
| :---------------- | :----------------------------------------------- | :-------------------------------------------------- |
| **Context**       | Own context window; results return to caller     | Own context window; fully independent               |
| **Communication** | Report results back to main agent only           | Teammates message each other directly               |
| **Coordination**  | Main agent manages all work                      | Shared task list with self-coordination             |
| **Best for**      | Focused tasks where only the result matters      | Complex work requiring discussion and collaboration |
| **Token cost**    | Lower                                            | Higher -- each teammate is a separate instance      |

Use agent teams when teammates need to share findings, challenge each other, and coordinate on their own. Use subagents when you need quick, focused workers that report results back.

Best use cases:
- **Research and review** -- multiple angles investigated simultaneously
- **New modules or features** -- each teammate owns a separate piece
- **Debugging with competing hypotheses** -- parallel theories, adversarial debate
- **Cross-layer coordination** -- frontend, backend, tests each owned by a different teammate

---

## Enabling

Add to `settings.json`:

```json
{
  "env": {
    "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"
  }
}
```

Or set the environment variable directly in your shell.

---

## Architecture

| Component     | Role                                                              |
| :------------ | :---------------------------------------------------------------- |
| **Team lead** | Main session -- creates team, spawns teammates, coordinates work  |
| **Teammates** | Separate Claude Code instances working on assigned tasks          |
| **Task list** | Shared work items that teammates claim and complete               |
| **Mailbox**   | Messaging system for inter-agent communication                   |

Storage locations:
- Team config: `~/.claude/teams/{team-name}/config.json`
- Task list: `~/.claude/tasks/{team-name}/`

Both are auto-generated. Don't edit config by hand -- it's overwritten on state updates.

Tasks have three states: **pending**, **in progress**, **completed**. Tasks can depend on other tasks; blocked tasks auto-unblock when dependencies complete. Claiming uses file locking to prevent race conditions.

---

## Display Modes

| Mode           | Description                                                  | Requirement          |
| :------------- | :----------------------------------------------------------- | :------------------- |
| **in-process** | All teammates in main terminal. Shift+Down to cycle.         | Any terminal         |
| **split panes**| Each teammate gets own pane. Click to interact.              | tmux or iTerm2       |
| **auto**       | Split panes if inside tmux; in-process otherwise (default).  | --                   |

Override globally in `~/.claude.json`:

```json
{
  "teammateMode": "in-process"
}
```

Or per-session: `claude --teammate-mode in-process`

---

## Invoking Agent Teams

There are three main ways an agent team gets created: by the **user** directly, by a **skill**, or by an **agent**. In all cases, the user describes what they want in natural language and Claude handles spawning.

### Invoked by the User

The most common path. Tell Claude to create a team and describe the task and structure.

**Example: Parallel code review**

```
Create an agent team to review PR #142. Spawn three reviewers:
- One focused on security implications
- One checking performance impact
- One validating test coverage
Have them each review and report findings.
```

**Example: Research from multiple angles**

```
I'm designing a CLI tool that helps developers track TODO comments across
their codebase. Create an agent team to explore this from different angles: one
teammate on UX, one on technical architecture, one playing devil's advocate.
```

**Example: Debugging with competing hypotheses**

```
Users report the app exits after one message instead of staying connected.
Spawn 5 agent teammates to investigate different hypotheses. Have them talk to
each other to try to disprove each other's theories, like a scientific
debate. Update the findings doc with whatever consensus emerges.
```

**Example: Specifying models and count**

```
Create a team with 4 teammates to refactor these modules in parallel.
Use Sonnet for each teammate.
```

### Invoked by a Skill

A skill's `SKILL.md` can instruct the agent to create a team as part of its workflow. The skill prompt describes the team structure and the agent executing the skill follows those instructions.

**Example: A `/deep-review` skill that spawns a review team**

```markdown
---
name: deep-review
description: Multi-perspective code review using an agent team
argument-hint: <PR number or file path>
---

## Behavior

When invoked, create an agent team with three reviewers:

1. **Security reviewer** -- audit for auth issues, injection, data exposure
2. **Performance reviewer** -- check for N+1 queries, unnecessary allocations, hot paths
3. **Correctness reviewer** -- verify edge cases, error handling, test coverage

Each reviewer works independently. When all finish, synthesize findings into
a single review summary grouped by severity (critical / warning / suggestion).

Require plan approval before any reviewer suggests code changes.
```

The user invokes it with `/deep-review #142` and the executing agent creates the team automatically.

**Example: A `/parallel-refactor` skill**

```markdown
---
name: parallel-refactor
description: Refactor multiple modules in parallel using an agent team
argument-hint: <module list or directory>
---

## Behavior

1. Scan the target directory and identify independent modules.
2. Create an agent team with one teammate per module (max 5).
3. Each teammate refactors its assigned module, runs tests, and reports results.
4. The lead validates no cross-module breakage and synthesizes a summary.
```

### Invoked by an Agent

An agent definition (the system prompt in an agent's `.md` file) can instruct the agent to create teams for appropriate tasks. This is useful for coordinator or manager agents that delegate complex work.

**Example: A coordinator agent that uses teams for large tasks**

In an agent's markdown definition:

```markdown
---
name: coordinator
description: Coordinates complex multi-part tasks across the codebase
---

You are a project coordinator. When a task involves three or more independent
workstreams, create an agent team to parallelize the work.

## Team creation guidelines

- Spawn one teammate per independent workstream
- Give each teammate a clear, scoped prompt with file paths and acceptance criteria
- Require plan approval for any teammate that will modify shared modules
- Wait for all teammates to complete before synthesizing results
- Clean up the team when done

## Example delegation

When asked to implement a new API endpoint:
- Spawn a **backend** teammate to implement the route and handler
- Spawn a **test** teammate to write integration tests
- Spawn a **docs** teammate to update the API documentation

Monitor progress and redirect teammates if they get stuck.
```

**Example: An agent that conditionally proposes a team**

```markdown
---
name: analyst
description: Investigates issues and proposes solutions
---

You investigate issues reported by the user.

For simple issues (single file, clear root cause), investigate directly.

For complex issues (multiple possible causes, cross-cutting concerns), propose
an agent team to the user:

"This looks like it could benefit from parallel investigation. I'd suggest
spawning teammates to test these hypotheses simultaneously:
- Teammate A: investigate the database connection pool
- Teammate B: check the rate limiter configuration
- Teammate C: audit recent deploy changes

Want me to create this team?"

Only create the team after user confirmation.
```

---

## Subagent Definitions as Teammates

When spawning a teammate, you can reference a subagent type by name. The teammate inherits the definition's `tools` allowlist, `model`, and appended system prompt instructions. Team coordination tools (`SendMessage`, task management) are always available regardless of `tools` restrictions.

```
Spawn a teammate using the security-reviewer agent type to audit the auth module.
```

Note: `skills` and `mcpServers` from the subagent definition are **not** applied to teammates. Teammates load these from project/user settings like a regular session.

---

## Controlling the Team

### Require plan approval

```
Spawn a designer teammate to refactor the authentication module.
Require plan approval before they make any changes.
```

The lead reviews and approves/rejects plans autonomously. Influence its judgment with criteria: "only approve plans that include test coverage."

### Talk to teammates directly

- **In-process:** Shift+Down to cycle, type to message. Enter to view session, Escape to interrupt. Ctrl+T toggles task list.
- **Split panes:** Click into a pane to interact.

### Task assignment

- **Lead assigns:** tell the lead which task goes to which teammate
- **Self-claim:** teammates pick up the next unassigned, unblocked task automatically

### Shut down and clean up

```
Ask the researcher teammate to shut down
```

```
Clean up the team
```

Always use the lead to clean up. Shut down all teammates before cleaning up.

---

## Hooks for Quality Gates

| Hook | Trigger | Exit code 2 effect |
| :--- | :------ | :----------------- |
| `TeammateIdle` | Teammate about to go idle | Send feedback, keep working |
| `TaskCreated` | Task being created | Prevent creation with feedback |
| `TaskCompleted` | Task being marked complete | Prevent completion with feedback |

---

## Best Practices

- **Give enough context in spawn prompts.** Teammates don't inherit the lead's conversation history. Include file paths, tech details, and acceptance criteria.
- **Start with 3-5 teammates.** More adds coordination overhead with diminishing returns.
- **Aim for 5-6 tasks per teammate.** Keeps everyone productive without excessive switching.
- **Avoid file conflicts.** Break work so each teammate owns different files.
- **Start with research/review tasks** if new to teams -- clear boundaries, no code conflicts.
- **Tell the lead to wait** if it starts implementing instead of delegating: "Wait for your teammates to complete their tasks before proceeding."
- **Pre-approve common operations** in permission settings to reduce prompt interruptions.

---

## Limitations

- No session resumption for in-process teammates (`/resume` and `/rewind` don't restore them)
- Task status can lag -- teammates sometimes fail to mark tasks complete
- One team per session; no nested teams
- Lead is fixed for lifetime -- can't promote a teammate
- All teammates start with the lead's permission mode
- Split panes require tmux or iTerm2 (not VS Code terminal, Windows Terminal, or Ghostty)
