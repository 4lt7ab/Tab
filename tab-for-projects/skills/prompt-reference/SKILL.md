---
name: prompt-reference
description: "Prompt quality conventions and reference — loads quality rules into context for preventive use"
argument-hint: "[project-name]"
---

# Prompt Quality Reference

Print this reference when invoked. Do not summarize — output the full content below.

## Trigger

Use this skill whenever:
- An agent is about to write or update task descriptions, plans, acceptance criteria, or KB documents
- The user asks about prompt quality, writing conventions for MCP content, or how to write good tasks
- The user explicitly invokes `/prompt-reference`

---

## Prompt Quality Conventions

Six rules for MCP content that agents consume. Apply these when writing or reviewing task descriptions, plans, acceptance criteria, and KB documents.

### Rule 1: No Unenforceable Constraints

Plans should not restate sandbox or runtime constraints the agent cannot violate anyway.

**Test:** If the agent ignores this instruction, does something different actually happen? If not, the constraint is noise — remove it.

### Rule 2: No Ambiguous Either/Or

Plans must not contain unresolved alternatives that force the developer to guess.

**Test:** Search for "either...or", "you can...or you can", "optionally", "consider" without resolution. Every alternative must be resolved to a single approach.

### Rule 3: Enum/Tag Accuracy

Plans must reference correct status values, tag names, and categories.

**Test:** Verify every enum value against the MCP schema. Common errors: invented statuses, nonexistent tags, wrong category names. Reference `/mcp-reference` for the canonical values.

### Rule 4: Scope-Dependent Accuracy

Descriptions must not misrepresent what the implementing agent will encounter.

**Test:** Cross-check the description against what the agent actually has access to — its tools, the codebase state, the MCP data available.

### Rule 5: No Phantom References

Plans must not reference files, APIs, tools, or agents that don't exist.

**Test:** Every named reference (file path, function name, tool name, agent name) should be verifiable. Flag suspicious references.

### Rule 6: Precise Guidance Over Blanket Bans

Prohibitions should not catch legitimate uses. Replace "never do X" with precise guidance that names the specific cases to avoid.

**Test:** Check if any "never" or "do not" instruction has legitimate exceptions. If so, rewrite to name the exceptions.

---

## Clarity Checklist

Beyond the six rules, check these when writing MCP content:

| Dimension | Good | Bad |
|-----------|------|-----|
| **Description clarity** | A developer agent with no prior context understands what to build and why | Assumes context not in the task |
| **Plan concreteness** | Names specific files, functions, and patterns | "Update the API," "add tests" |
| **Acceptance criteria** | Each criterion is mechanically verifiable | Requires judgment calls to evaluate |
| **Field completeness** | Description, plan, and acceptance_criteria all populated for medium+ effort | High-effort task with no plan |
| **Effort alignment** | Effort estimate matches the apparent scope of the plan | Trivial effort on a multi-file change |

## Document Quality

When writing KB documents:

- **Scanability:** Headings should be descriptive ("Error Response Shape"), not generic ("Notes").
- **Instruction concreteness:** State practices as concrete instructions with examples, not abstract principles.
- **Example quality:** Show input/output pairs, not just prose descriptions of behavior.
- **Structure:** Put structured data in tables rather than burying it in paragraphs.
