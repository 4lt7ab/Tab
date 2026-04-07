---
name: design
description: "Take a feature idea, research the codebase, design the approach, and produce a planned backlog of tasks ready for implementation."
argument-hint: "[project ID or name]"
---

# Design

Turn a feature idea into a backlog someone can build from tomorrow.

## Trigger

**When to activate:**
- User invokes `/design`
- User says "let's design," "break this down," "plan out the feature," "how should we build this"
- User describes a new feature and wants it decomposed into buildable work

**When NOT to activate:**
- Work items already exist and need implementing — that's `/develop`
- User wants to extract tasks from a past conversation — that's `/retro`
- User wants to refine or re-scope existing tasks — work with them directly, no skill needed

## Requires

- **MCP:** tab-for-projects (`get_project`, `list_projects`, `list_tasks`, `create_task`, `update_task`, `get_dependency_graph`, `list_documents`, `get_document`, `create_document`, `update_project`)
- **Agents:** `tab-for-projects:developer` — dispatched for analysis, never implementation
- **Context:** A feature idea with enough substance to design against. Can be a sentence or a spec — the skill adapts. If it's too vague to decompose, the skill interviews the user until it isn't.

## Session Lifecycle

### 1. Understand the feature

Start with what the user gave you. It might be a sentence, a paragraph, or a detailed spec. Your job is to figure out what's load-bearing and what's still soft.

**Identify the project.** Resolve via argument, conversation context, or ask. Load the project via `get_project` — goal, requirements, and linked documents frame every design decision.

**Interview if needed.** If the feature description has gaps that would change the design, ask. But ask efficiently — batched questions, not a drip feed. The goal is to reach "enough to design against," not "enough to write the user manual."

Questions that earn their keep:
- What's the scope boundary? (What is explicitly *not* part of this?)
- Are there constraints? (Must use X, can't touch Y, needs to ship by Z)
- Who's the user? (End user, developer, internal tooling, API consumer)
- What does success look like? (Performance target, UX outcome, integration point)

Questions that don't:
- Anything the codebase already answers
- Anything the KB documents already answer
- Implementation details the user doesn't care about

### 2. Research the codebase

This is where the skill earns its keep. Design without codebase research is fiction.

**What you're looking for:**

| Question | Why it matters |
|---|---|
| Where does this feature live? | Determines file structure, module boundaries, affected layers |
| What exists today? | The feature might extend something, replace something, or need to coexist with something |
| What patterns are established? | New code should match. Introducing a new pattern is a design decision, not an accident |
| What are the integration points? | Where the feature touches existing behavior — these are the risky seams |
| What test infrastructure exists? | Knowing the test patterns shapes how you write acceptance criteria |

**How to research efficiently:**

For a small, focused feature — do it yourself. Read the relevant files, trace the data flow, check the test patterns. You have the tools and the context window.

For a large feature spanning multiple areas — dispatch developers in **analysis mode**. Each developer explores one area and returns findings. This is the same developer agent, but dispatched for analysis, not implementation:

```
scope:          what to investigate (files, directories, subsystem, question)
project_id:     the project context
document_ids:   relevant KB documents for comparison
```

Dispatch analysis in parallel when investigating independent areas. Wait for all reports before designing — half-informed design is worse than slow design.

**Check the KB.** Search for architecture decisions, conventions, and prior art. If someone already designed a related feature, learn from it — or learn from its mistakes.

```
list_documents({ project_id: "...", tag: "architecture" })
list_documents({ project_id: "...", tag: "conventions" })
list_documents({ project_id: "...", search: "<feature-relevant terms>" })
```

### 3. Design the approach

Now you know the feature, the codebase, and the constraints. Synthesize.

**Produce a design summary for the user:**

- **Approach.** How the feature works, in 2-5 sentences. Not implementation details — the conceptual model.
- **Where it lives.** Which modules, files, layers are involved. New files vs. modifications.
- **Key decisions.** Choices that have trade-offs. Don't hide them — surface them with your recommendation and reasoning.
- **Risks.** What could go wrong. Integration seams, performance concerns, scope creep vectors.
- **Open questions.** Anything you couldn't resolve from the codebase or KB alone.

Present this to the user. Discuss. Iterate. The design summary is a conversation, not a deliverable — it's meant to be poked at, challenged, and refined.

Do not proceed to task creation until the user is satisfied with the approach. Shipping a beautiful backlog built on a bad design is just organized regret.

### 4. Decompose into tasks

Once the approach is agreed, break it into tasks.

**Task shape:**

```
title:                imperative verb phrase — "Add webhook registration endpoint"
summary:              what and why, 1-3 sentences
category:             feature | bugfix | refactor | test | perf | infra | docs | security | design | chore
effort:               trivial | low | medium | high | extreme
acceptance_criteria:  testable conditions for "done" — specific, not vibes
group_key:            shared key for related tasks (e.g., "webhook-core")
```

**Decomposition principles:**

- **Each task is independently shippable.** It can be committed, tested, and merged without other tasks from this design being done. If it can't, it has a dependency — declare it.
- **Right-size for a single developer session.** A task marked `medium` should take one focused developer dispatch. If you're writing "and then also" in the summary, it's two tasks wearing a trenchcoat.
- **Plans are mandatory for medium and above.** A plan answers: "If a developer sat down to build this with no other context, what would they need to know?" Include the approach, specific files, sequencing within the task, patterns to follow, edge cases, and testing strategy.
- **Acceptance criteria are testable.** "Works correctly" is not a criterion. "Returns 400 with validation errors when payload is missing required fields" is.
- **Dependency order matters.** Schema before API before UI. Foundation before features. The dependency graph should be a DAG, not a wish.

**Extreme tasks get flagged, not created.** If a task is sized `extreme`, it needs further decomposition. Either break it down now or create it as a design task whose output is a more granular plan.

### 5. Present for review

Show the full task list with all fields. Group by `group_key`. Show the dependency graph — which tasks block which.

```
[group: webhook-core]
1. Define webhook event schema          trivial   feature   (no deps)
2. Add webhook registration endpoint    medium    feature   (depends on 1)
3. Build async delivery pipeline        medium    feature   (depends on 1)
4. Add retry logic with backoff         medium    feature   (depends on 3)

[group: webhook-ui]
5. Create webhook management dashboard  medium    feature   (depends on 2)
6. Add delivery log viewer              low       feature   (depends on 3)
```

The user reviews: keep, edit, drop, reorder, add, re-scope. This is the last gate before tasks become real. Take the feedback seriously — a task the user doesn't believe in is a task that rots in the backlog.

### 6. Create and connect

Batch-create approved tasks via `create_task`. Then wire up dependencies via `update_task`.

After creation:
- Report the final task count, groups, and dependency structure
- Note any design decisions worth capturing in the KB — offer to create documents
- Suggest next steps: refine specific tasks, start a `/develop` session, or let it marinate

## Decision Framework

### When to dispatch analysis vs. explore yourself

| Situation | Action |
|---|---|
| Feature touches 1-2 modules you can read in a few files | Explore yourself |
| Feature spans 3+ independent areas | Dispatch parallel analysis developers |
| You need to understand a deep call chain or data flow | Dispatch a developer with a specific question |
| You need to verify a pattern across many files | Dispatch — that's grunt work, not thinking |

Analysis dispatches are cheap context-wise — you send a question, you get back findings. The developer reads the code so you don't have to fill your context window with implementation details you won't need.

### When to stop designing and start asking

- The feature implies a product decision (pricing, permissions, user-facing behavior) — that's the user's call
- Two valid approaches exist with meaningfully different trade-offs — present both, recommend one, let the user choose
- The codebase contradicts what the user described — surface it before building on a false foundation
- Scope is creeping — name it: "This started as X, it's becoming Y. Which do you want?"

### When a design session becomes a working session

Sometimes the user says "looks good, let's build it" mid-session. That's a natural handoff to `/develop`. You already have the context — transition cleanly:

1. Finish creating any remaining tasks
2. Note that you're switching to implementation mode
3. Follow the `/develop` workflow from step 2 onward — you've already done most of the context gathering

## Constraints

- **Design is the product, not tasks.** Tasks are how the design gets tracked. If the design is wrong, perfect tasks don't save you.
- **Never create tasks before the user approves the approach.** The review gate on the design summary is non-negotiable.
- **Never fabricate codebase knowledge.** If you haven't read it, you don't know it. "I assume this module handles X" is a bug in a design document.
- **Respect existing architecture.** A design that ignores established patterns needs to justify the departure. "I didn't notice" is not a justification.
- **Flag scope explicitly.** The user said "add webhook support." If your design includes a full event bus rewrite, that's a scope expansion — name it and get buy-in.
- **Plans reference real files.** A plan that says "modify the relevant handler" is not a plan. A plan that says "modify `src/api/handlers/events.ts`, extending the `EventHandler` class" is.
