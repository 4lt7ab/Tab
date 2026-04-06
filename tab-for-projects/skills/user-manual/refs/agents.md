# Agentic Reference

## File Anatomy

### Agent File

```
---
name: {name}
description: "{one-sentence role}"
skills:
  - user-manual
---

{Opening narrative — 2-3 sentences.}

## Role
{Numbered responsibilities}

## How It Works
{Phase-based subsections}

## Constraints
{Behavioral boundaries}
```

Frontmatter requires `name` + `description`. All other fields are opt-in.

#### Supported Frontmatter (Plugin Agents)

| Field | When to use |
|-------|------------|
| `name` | **Always.** Lowercase, hyphens. |
| `description` | **Always.** One sentence — specific enough for delegation matching. |
| `skills` | When the agent needs reference knowledge on most invocations. Preloads full skill content at startup. Don't preload skills used only occasionally — invoke them on demand instead. |
| `tools` | When the agent should be restricted to specific tools. Omit to inherit all tools. Use `Agent(name1, name2)` syntax to restrict which subagents can be spawned. |
| `disallowedTools` | When you need to remove specific tools (e.g., prevent an analyst agent from editing files). Prefer this over `tools` when you only need to block a few. |
| `model` | Rarely. Prefer setting at invocation time. Use in frontmatter only when the agent fundamentally requires a specific model (e.g., an agent that needs Opus-level reasoning). |
| `maxTurns` | When the agent has a bounded workflow that should stop after N turns. Safety net against runaway agents. |
| `effort` | Rarely. Let the dispatcher or session control this. |
| `isolation` | Set to `worktree` for agents that modify the codebase and might need rollback. |
| `memory` | When the agent should learn across sessions. Use `project` scope for project-specific learning. |
| `background` | When the agent should always run as a background task. Rare — usually controlled at invocation. |

**Not supported in plugins:** `hooks`, `mcpServers`, `permissionMode`.

### Skill File

```
---
name: {name}
description: "{what it does — specific enough for trigger matching}"
argument-hint: "{pattern or (no arguments)}"
---

# {Title}

{What this is and why it exists — one paragraph.}

## Trigger
{DO and DON'T lists}

## {Main Body}
{Steps, phases, or reference content — depends on mode}
```

Frontmatter: `name` + `description` + `argument-hint`.

---

## Opening Narrative

The paragraph before any heading sets identity and scope. It answers three questions:

1. What is this agent?
2. What does it do?
3. What doesn't it do?

In 2-3 sentences. This is the single highest-leverage paragraph in the file — LLMs use it to calibrate every decision that follows.

**Strong openings establish boundaries through contrast:**

> "A dispatch agent that manages project workflows by routing work to the right agents. The manager reads project state, understands what phase the work is in, and spawns the agent that moves it forward. It does very little work itself — its job is to know which agent does what and when."

What makes this work: "It does very little work itself" draws the line. The agent now knows that doing substantive work is a violation, not a feature.

> "A task executor that turns planned work into committed code. Where dispatch decides what to work on and in what order, the developer does the work."

What makes this work: "Where dispatch decides" positions this agent relative to another. The developer doesn't need a constraint saying "don't decide what to build" — the opening already framed it.

**Anti-pattern:** "This agent helps with projects and does various tasks." No boundaries, no contrast, no calibration.

---

## Roles

A numbered list of 3-5 responsibilities under `## Role`. Each item: **bold verb** + one-clause elaboration.

| Convention | Example |
|-----------|---------|
| Action verb, present tense | **Reads** — loads project state from the MCP |
| One behavior per item | Not "reads and analyzes" |
| Verb describes the action, clause describes the scope | **Dispatches** — spawns the right agent with a clear brief |

**The Role section is a contract.** If something isn't listed here, the agent shouldn't be doing it. If the agent does it, it should be listed here. This bidirectional alignment is what makes roles useful — they're not decoration, they're boundaries.

**Anti-patterns:**
- State descriptions: "Is responsible for quality" → **Verifies** acceptance criteria are met
- Vague scope: "Handles things" → **Routes** blocked tasks to the appropriate agent
- Compound items: "Reads, analyzes, and decides" → three separate items

---

## Workflows

Organize under `## How It Works` with named phase subsections. Each phase describes one stage of execution.

### Phase Design

Name phases after what happens: "Assess," "Dispatch," "Gather Context" — not "Phase 1," "Step 2."

Each phase should answer:
- **Entry:** What condition puts the agent in this phase?
- **Action:** What does the agent do here?
- **Exit:** What condition moves it to the next phase?

Phases should be independently readable. A reader jumping to "### Gathering Context" should understand what gathering context means without reading everything before it.

### Decision Tables

When an agent makes a routing or branching decision, use a table:

| Condition | Action |
|-----------|--------|
| Requirements exist but design is empty | Dispatch tech lead |
| Tasks exist and are unblocked | Dispatch developer |
| Tasks are in_progress | Monitor — don't double-dispatch |

Tables surface decision logic that prose buries. Any time you write "if X then Y, but if Z then W" — convert it to a table.

### Dispatch Briefs

When an agent spawns a subagent, show the brief as a code block:

```
You are the [role] for project [name] (ID: [id]).

Scope: [bounded description of what to do]
Context: [IDs and summaries — not full content]

[One clear instruction of what to produce]
```

Briefs make subagents self-sufficient. They include IDs so the subagent can fetch its own context. They do NOT inline full content — that wastes the parent's context window and makes the brief brittle.

### Tool Calls

Show MCP calls or tool usage patterns as code blocks within the phase where they're used:

```
list_tasks({ project_id: "...", status: ["todo", "in_progress"] })
```

This gives the LLM a concrete invocation template, not a description to interpret.

### Ceremony Scaling

Not every invocation needs every phase. Good workflows say which phases to skip and when:

> **Trivial / Low effort — fast path:** Read the task and relevant code. Make the change. Commit.
>
> **High effort — full ceremony:** Gather context thoroughly. Write tests first. Implement. Review your own changes. Commit with a detailed message.

This prevents over-engineering simple tasks and under-engineering complex ones.

---

## Constraints

Bullet list under `## Constraints`. Each item: **bold rule** + explanation sentence.

### Five Rules for Constraints

**1. Enforceable.** The agent must have the ability to violate this. If the runtime already prevents it (no tool access, sandbox), the constraint is noise — remove it.

*Test:* "If the agent ignores this, does something different happen?"

**2. Specific.** Name the exact behavior to avoid and what to do instead.

| Weak | Strong |
|------|--------|
| Don't do too much | Don't modify code outside the task scope |
| Be careful with data | Never fetch full document content — work in summaries and IDs |
| Follow best practices | Match existing patterns in the codebase — consistency over preference |

**3. Exception-aware.** If "NEVER" has legitimate exceptions, name them. Blanket bans that catch good behavior get ignored entirely.

| Blanket | Precise |
|---------|---------|
| NEVER modify other files | Don't modify files outside the task scope. Integration points (imports, registrations) are expected when the task requires them. |
| NEVER create tasks | The developer doesn't create tasks. If you find gaps, document them in the implementation field. |

**4. Calibrated language.** "NEVER" and "must not" for hard invariants. "Avoid" and "prefer" for soft guidance. Don't use "NEVER" for preferences — it dilutes the signal.

**5. Scoped to 3-6 items.** Fewer than 3 suggests missing boundaries. More than 6 suggests the agent's scope is too broad or constraints are too granular.

**Anti-patterns:**
- Restating runtime limits (sandbox, tool access restrictions)
- Motivational filler: "Be thorough and helpful"
- Contradicting the workflow: workflow says do X, constraint says don't do X

---

## Triggers (Skills)

Every skill needs a `## Trigger` section with explicit **When to activate** and **When NOT to activate** lists.

### The DO List

Concrete conditions, not vibes:

```markdown
**When to activate:**
- The user asks to capture knowledge from completed work
- A task is marked done and the user wants to extract learnings
```

### The DON'T List

This prevents false positives. Without it, skills activate on adjacent requests:

```markdown
**When NOT to activate:**
- The user wants to edit an existing document (normal editing)
- The user asks about plugin-level scaffolding (different scope)
- The user wants prompt quality rules (that's /user-manual prompts)
```

**Write DON'T items by asking:** "What's a request that sounds similar but should go somewhere else?"

### Description for Trigger Matching

The `description` frontmatter is what the runtime uses for matching. It must be:

- **Specific enough to trigger correctly.** "Capture knowledge from completed work" triggers on knowledge capture.
- **Distinct enough to avoid false positives.** Not "helps with documentation" — that matches everything about docs.

*Test:* If an LLM saw this description in a catalog of 20 skills, would it trigger this one correctly and NOT trigger it for similar requests?

---

## Skill Modes

The mode determines the body structure:

| Mode | Structure | Example |
|------|-----------|---------|
| **One-shot** | Numbered protocol steps — execute and produce output | Load context → research → check → write |
| **Sustained** | Entry → active state → exit condition → synthesis | `/think`: orient → draw out → stop → write |
| **Reference** | Structured content printed verbatim | `/user-manual mcp`: print content, done |

**One-shot** skills are procedures. Each step has clear inputs and outputs. The skill runs once and produces a result.

**Sustained** skills are modes. The user enters a state — the skill defines how to behave in that state, when to exit, and what to produce on exit.

**Reference** skills are context loaders. They dump structured knowledge into the conversation. The opening line is: "Print this reference when invoked. Do not summarize — output the full content below."

### Argument Handling

Define behavior for all cases:

- **With argument:** What happens. "If the user passes a project name, resolve it against `list_projects`."
- **Without argument:** What happens. "Ask which project to document."
- **No arguments expected:** Use `argument-hint: "(no arguments)"`.

---

## Output Specification

Every agent and skill should make clear what it produces. For agents, this lives in the workflow phases. For skills, it gets a dedicated section or is embedded in the protocol.

**Specify the shape, not just the type:**

| Vague | Concrete |
|-------|----------|
| Produces a document | Creates a KB document with `create_document`, tags it `conventions` + `architecture`, and attaches it to the project |
| Returns results | Returns: summary (2-3 sentences), tasks created (IDs + titles), design questions (if any), out-of-scope findings |
| Commits code | Creates a commit: `<type>: <description>`, includes task ID, one logical change per commit |

---

## Composition Patterns

### Tables Over Prose

Whenever content involves choices, comparisons, or mappings — use a table. This applies to:
- Decision routing (condition → action)
- Field descriptions (field → what to write)
- Quality checklists (dimension → good → bad)
- Pattern catalogs (pattern → when to use)

### Code Blocks for Templates

Anything the agent will produce or invoke goes in a code block: dispatch briefs, MCP calls, commit messages, output shapes. Code blocks give the LLM a fill-in template rather than a description to interpret.

### Proportional Length

Match file length to decision density:

| Complexity | Lines | Signal |
|-----------|-------|--------|
| Focused, few decisions | 60-120 | Single responsibility, linear flow |
| Moderate branching | 120-220 | Some routing, multiple phases |
| Complex orchestration | 220-370 | Many branches, subagent coordination |

If a file exceeds 370 lines, the scope is probably too broad. Split into an agent + skill, or decompose the agent.

### Voice

- **Agents:** Second person ("You are...") or third person ("The manager...") in the opening. Imperative in workflows ("Read the task," "Dispatch the developer").
- **Skills:** Imperative throughout ("Print this reference," "Ask which project").
- Present tense. Direct language. Short sentences for rules, longer for explanations.
- No hedging: "consider perhaps" → "do this when."
