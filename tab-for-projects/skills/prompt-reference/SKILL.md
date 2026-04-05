---
name: prompt-reference
description: "Prompt quality conventions and reference — loads quality rules into context for preventive use, or audits existing MCP content."
argument-hint: "[project-name] [--audit]"
---

# Prompt Quality Reference

Print this reference when invoked. Do not summarize — output the full content below. When `--audit` is passed, run the audit protocol instead.

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

Plans must not contain unresolved alternatives that force the implementer to guess.

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

---

## Audit Mode (--audit)

When invoked with `--audit`, run a structured review of existing MCP content instead of loading the reference.

### Audit Protocol

1. **Resolve the project.** If the user provided an argument, match it against `list_projects`. Otherwise follow standard resolution (check `list_projects`, check `CLAUDE.md`, ask if ambiguous).

2. **Load project context.** Call `get_project` for the goal, requirements, and design.

3. **Fetch the Prompt Quality Conventions document.** Call `list_documents` and search for the document by title containing "Prompt Quality Conventions" or tagged `conventions`. If no conventions document is found, use the six rules above and note the absence.

4. **Load review targets.** Call `list_tasks` filtering for `status: ["todo", "in_progress"]`. For large backlogs (>15 tasks), prioritize high and extreme effort tasks first.

5. **Review each task.** Call `get_task` for full details. Apply the six rules as a mechanical checklist. Assess clarity per the checklist above. Classify each finding:

   | Severity | Meaning |
   |----------|---------|
   | **Blocking** | Will cause the implementing agent to fail or produce wrong output |
   | **Improvement** | Won't cause failure but reduces implementation quality |
   | **Clean** | No issues found |

6. **Review documents.** Call `list_documents` for the project. For each document, call `get_document` and evaluate against the document quality criteria above.

7. **Present findings.** Report in this structure:

   ```
   ## Prompt Audit: [Project Name]

   ### Task Findings
   | Task | Title | Severity | Finding | Suggested Fix |
   |------|-------|----------|---------|---------------|

   ### Document Findings
   | Doc | Title | Severity | Finding | Suggested Fix |
   |-----|-------|----------|---------|---------------|

   ### Summary
   - Tasks reviewed: [N]
   - Blocking: [N], Improvements: [N], Clean: [N]
   - Documents reviewed: [N]
   ```

   Omit empty severity categories. Adapt columns to fit actual findings.

8. **Offer to apply fixes.** Three options: fix all, walk through one at a time, or report only. When applying fixes, only modify `description`, `plan`, and `acceptance_criteria` on tasks; `content` and `title` on documents. Never modify `status`, `effort`, `impact`, or `category`.
