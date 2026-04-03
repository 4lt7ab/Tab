# Agent Conventions

Three structural rules at the seams. The workflow in the middle is fully agent-specific.

## 1. Opening Paragraph

Three sentences, always in this order:

1. **Role** — what this agent is and what it produces.
2. **Invocation** — how it's triggered and what it receives.
3. **Constraint** — the single most important boundary (who it talks to, what it doesn't do).

This is the highest-weight position in the prompt. Standardizing it costs nothing per agent and buys reliable orientation.

## 2. Shared Vocabulary

Cross-cutting operations use canonical names. Agent-specific operations use agent-specific names.

| Canonical term | Meaning | Used by |
|---|---|---|
| **Load Context** | The MCP-reading phase — pull project, task, and document data before doing work. Every agent's first workflow step. | All agents |
| **Return** | The final output sent back to the caller. What the caller gets and what it contains. | Headless agents |

Everything else — codebase research, verification, writing knowledge, pair programming — is agent-specific and named for what the agent actually does. The planner's "Research the Codebase" is exploration. QA's "Inspect the Actual Work" is verification. The documenter's "Research the Codebase" is extraction. These are different operations that happen to involve reading code. Don't flatten them.

## 3. Boundaries

Every agent closes with explicit boundaries: what it does NOT do and how it hands off. For headless agents, this is a `## Boundaries` section. For conversational agents, the boundaries are woven into the agent's structure where they carry the most weight (e.g., the manager's hard rule at the top).

Boundaries are short, declarative, and unnegotiated. They answer: if the agent is tempted to do X, should it? The answer is always no — hand it off.
