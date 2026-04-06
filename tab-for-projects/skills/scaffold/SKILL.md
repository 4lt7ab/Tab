---
name: scaffold
description: "Scaffold new agent and skill files — walks through the design, writes the file, and registers it in plugin.json."
argument-hint: "agent <name> | skill <name>"
---

# Scaffold

A conversational skill that guides writing new agent and skill files for the Claude Code plugin system. You interview the user about what they're building, produce the file, and handle registration.

This skill activates **only** when the user runs `/scaffold`.

## Trigger

**When to activate:**
- The user runs `/scaffold` with or without arguments
- The user asks to create a new agent or skill for a plugin

**When NOT to activate:**
- The user wants to edit an existing agent or skill (that's normal editing)
- The user asks about plugin-level scaffolding (creating an entire plugin from scratch)
- The user asks about `settings.json` or marketplace manifest changes

## Step 1: Parse Intent

The argument tells you what to create:
- `/scaffold agent monitor` -- new agent named "monitor"
- `/scaffold skill deploy` -- new skill named "deploy"
- `/scaffold` (no args) -- ask: "Agent or skill? What's the name?"

Ask which plugin package to target. List the directories that contain a `.claude-plugin/plugin.json` file. Do not assume -- the user may be adding to any plugin in the repository.

## Step 2: Load Context

Before the interview, load knowledgebase documents that will inform the writing. Search dynamically -- do not assume specific documents exist.

Run these searches using `list_documents`:
1. Search for documents tagged `conventions` that cover agent construction patterns or prompt engineering.
2. Search for documents tagged `architecture` that cover agent/skill design principles or the agent-skill boundary.
3. Search for documents about prompt quality -- conventions for writing prompts that work.

For each search, scan the returned titles and summaries. Call `get_document` only for documents that are directly relevant to what the user is building. Cap at 3 documents total -- more dilutes context without improving output.

If no relevant documents exist, proceed without them. The templates below are self-contained.

## Step 3: Interview

Ask questions one at a time. After each answer, reflect back what you understood in one sentence before asking the next question. If the user's answer is clear and complete, move on -- do not over-interview.

### For Agents

Ask these five questions in order:

**1. Role in one sentence.** "What does this agent do?" The answer becomes the `description` frontmatter and the opening paragraph. If the answer is longer than one sentence, distill it and confirm.

**2. Responsibilities.** "What are the 3-5 things this agent is responsible for?" Each becomes a numbered item in the Role section. Press for verbs -- responsibilities are actions, not nouns.

**3. Workflow.** "Walk me through what happens when this agent runs. What triggers it? What does it do first? What decisions does it make? What does it produce?" This becomes the How It Works section with phase-based subsections. If the user describes a linear process, ask about decision points and branches.

**4. Boundaries.** "What must this agent NEVER do? What's explicitly out of scope?" This becomes the Constraints section. If the user only gives 1-2 constraints, prompt for more by asking about adjacent agent roles: "Should this agent ever [write code / create documents / make design decisions / manage tasks]?"

**5. Tools and patterns.** "Does this agent spawn subagents? Use MCP tools? Read code? Write code? What tools does it need?" This shapes the workflow sections and determines what code-block templates (dispatch briefs, MCP calls, decision tables) to include.

### For Skills

Ask these five questions in order:

**1. What it does in one sentence.** Becomes the `description` frontmatter. Must be clear enough for trigger matching -- test it by asking yourself: "If an LLM saw this description in a skill catalog, would it know when to activate this skill?"

**2. Trigger rules.** "When should this activate? When should it NOT?" Produce both a DO list and a DON'T list. If the user only describes positive triggers, ask about false positives: "What's something that sounds similar but should NOT trigger this skill?"

**3. Arguments.** "What does it accept? Required or optional?" This becomes `argument-hint`. Also determine behavior with and without arguments.

**4. Mode of operation.** "Is this one-shot (produce output and done), sustained (enter a mode the user exits later), or a reference dump (output content verbatim)?" This determines the body structure:
- One-shot: protocol with numbered steps
- Sustained: entry, active state, exit, synthesis
- Reference dump: structured content to print

**5. Output format.** "What does success look like? A file? A conversation? A structured report? Something else?" Specify the exact shape of the output so the skill produces consistent results.

### Shortcut

If the user provides all inputs upfront (e.g., "skip the interview, here's what I want: ..."), accept them. Map each input to the corresponding question above and confirm what you have before writing.

## Step 4: Write the File

Before writing, run quality checks against the draft (see Step 4a below). Then produce the complete markdown file.

**File locations:**
- Agent: `<plugin>/agents/<name>.md`
- Skill: `<plugin>/skills/<name>/SKILL.md`

Create the directory if it doesn't exist (skills only -- agents go in the existing `agents/` directory).

### Agent Template

```markdown
---
name: {name}
description: "{one-sentence role description}"
---

{Opening narrative paragraph -- 2-3 sentences establishing identity and purpose. Written in second person ("You are...") or third person ("The {name} agent..."). Sets the tone for everything below.}

## Role

1. **{Verb}s** -- {what this responsibility involves}
2. **{Verb}s** -- {what this responsibility involves}
3. **{Verb}s** -- {what this responsibility involves}

## How It Works

### {Phase 1 Name}

{What happens in this phase. Include MCP calls, subagent briefs, or decision logic as appropriate.}

### {Phase 2 Name}

{Continue for each phase of the workflow.}

## Constraints

- **{Hard boundary}.** {Why this matters.}
- **{Another constraint}.** {Explanation.}
- **{Another constraint}.** {Explanation.}
```

**Agent structural conventions to enforce:**

| Element | Convention |
|---------|-----------|
| Frontmatter | Exactly `name` + `description`, nothing else |
| Opening | Narrative paragraph before first heading |
| Role section | Numbered list, 3-5 items, each starts with bold verb |
| How It Works | Phase-based subsections |
| Decision logic | Tables (when/then) for routing or branching |
| Templates/briefs | Code blocks for dispatch briefs, MCP calls, output shapes |
| Constraints | Bullet list, strong language (NEVER, must not), 3-6 items |
| Length | 80-370 lines depending on complexity |

### Skill Template

```markdown
---
name: {name}
description: "{what the skill does -- clear enough for trigger matching}"
argument-hint: "{argument pattern or (no arguments)}"
---

# {Title}

{One paragraph explaining what this skill is and why it exists.}

## Trigger

**When to activate:**
- {Condition 1}
- {Condition 2}

**When NOT to activate:**
- {Exclusion 1}
- {Exclusion 2}

## {Workflow / Protocol / Instructions}

{The main body -- structure depends on mode:}

{For one-shot skills: numbered protocol steps}
{For sustained skills: entry, active state, exit conditions, synthesis}
{For reference skills: structured content to output verbatim}

## Output

{What the skill produces and its exact shape.}
```

**Skill structural conventions to enforce:**

| Element | Convention |
|---------|-----------|
| Frontmatter | `name` + `description` + `argument-hint` |
| Trigger section | Explicit DO and DON'T lists |
| Argument handling | Describe behavior with and without args |
| Output format | Specify exactly what success looks like |
| Principles | End with design principles if the skill involves judgment calls |
| Length | 60-220 lines |

### Step 4a: Quality Checks

Before writing the file, validate the draft against these six rules. Fix violations before producing output.

**1. No unenforceable constraints.** Every constraint in the Constraints section must govern a behavioral choice the agent actually makes. If the runtime already enforces it (sandbox, tool access), remove it. Test: "If the agent ignores this, does something different happen?"

**2. No ambiguous either/or.** If the draft presents two approaches, resolve which one to use -- or specify the decision criteria for choosing at runtime. Search for "either...or", "you can...or you can", "optionally" without resolution.

**3. Enum and tag accuracy.** If the draft references MCP statuses, tags, categories, or effort values, verify them against the actual schema. Do not invent values.

**4. No phantom references.** Every tool name, agent name, file path, and concept referenced in the draft must exist. Do not reference agents, skills, or tools that haven't been built.

**5. Precise guidance over blanket bans.** If a constraint says "NEVER do X", check whether there are legitimate exceptions. If so, rewrite to name the specific cases to avoid and the exceptions where it's appropriate.

**6. Scope-dependent accuracy.** If the draft describes another agent's or skill's behavior, verify the description matches what that agent or skill actually does. Don't misrepresent capabilities.

## Step 5: Register

**For agents:**
1. Read `<plugin>/.claude-plugin/plugin.json`
2. Add `"./agents/<name>.md"` to the `agents` array
3. Write the updated file

**For skills:**
- Skills auto-discover from the `skills/` directory reference in `plugin.json`. No registration change needed.
- Confirm to the user that the skill will be picked up automatically.

## Step 6: Verify

1. Read back the created file to confirm it was written correctly.
2. Show the user a summary: what was created, where it lives, and whether `plugin.json` was updated.
3. Suggest running the plugin validator if one exists: `scripts/validate-plugins.sh`.

## Principles

- **Interview, don't interrogate.** The value is in the guided decisions. If the user already knows what they want, get out of the way. If they're fuzzy, the questions help them think it through.
- **Concrete templates over abstract instructions.** The templates above are structural blueprints. Fill them with the user's specific content -- do not produce generic placeholders like "{add details here}".
- **Match existing patterns.** Before writing, read 1-2 existing agents or skills in the target plugin to match their tone, structure, and level of detail. The new file should look like it belongs.
- **One file, complete.** The output is a single markdown file that works without modification. No TODOs, no placeholders, no "fill this in later."
