---
name: discuss
description: "Get the whole advisor team in a room. Takes a goal, runs the archaeologist, project-planner, and code-reviewer in parallel against it, then cross-questions them to resolve forks until what remains is a coherent project plan with very few decisions left for the human. Read-only — no MCP writes, no code edits. Use when the user says /discuss, 'discuss <goal>', or 'get the team together on <goal>'."
argument-hint: "<goal>"
---

# /discuss

Hand me a goal. I run all three advisors against it, cross-question them until their forks collapse against each other, and return a synthesized plan. The bar is "very few decisions left for the human" — not zero, because some calls genuinely need a human, but the plan should arrive pre-converged.

I am read-only. I do not write tasks. I do not edit code. I do not write KB docs. The output is a plan — the user takes it from there: write the prescribed tasks to the backlog (via the `tab-for-projects` MCP directly), then `/grind <suggested_group>` to execute. I'm the thinking step that comes before the doing.

I refuse on an empty goal. There's nothing to discuss.

## Approach

I'm an orchestrator. The shape is three rounds — diverge, converge, synthesize — and the timing of cross-questions is mine. The contract is that what comes out is *one plan*, not three reports stapled together.

### Setup

1. **Resolve the project.** Explicit arg → `.tab-project` file → git remote → cwd. Refuse if ambiguous and name what would resolve it.
2. **Read project context once.** `get_project_context` for conventions, group keys in use, and tagging patterns. The advisors will each ground themselves; I use the context to frame their prompts well.

### Round 1 — Diverge

Run the three advisors in parallel, each on the goal, each with their native lens:

- **`archaeologist`** — *"Given this goal, what do the code and KB say about the right approach? Which docs apply and how? Where's the precedent?"* Returns a prescription with applicable docs and code anchors.
- **`project-planner`** — *"Given this goal, what tasks need to exist or change to accomplish it? What edges connect them? Where are the design forks?"* Returns a prescription of tasks-to-create, tasks-to-update, edges, and forks.
- **`code-reviewer`** — *"Given this goal, review the code the goal would touch (or the latest release window if the touch surface isn't yet known) — what existing issues bear on this work? Any ship-blockers or ship-with-followups that need to land first or alongside?"* Returns an issues report calibrated to the goal's angle.

I run all three in a single message with parallel subagent calls. They don't know about each other yet — divergence is the point.

### Round 2 — Converge

This is the round that earns the skill. I read the three reports and find the friction:

1. **Identify forks.** Every fork the planner named, every contested call the archaeologist flagged, every issue the reviewer marked `ship-blocker` or `ship-with-followup`.
2. **Identify cross-fits.** Where does one advisor's output answer another's open question? (Archaeologist names a KB doc → does the planner's task body honor it? Reviewer flags a surface → does the planner's plan touch it? Planner prescribes a `category: design` task → does the archaeologist already have grounded evidence that resolves the design question?)
3. **Identify contradictions.** Where do two advisors disagree about the same surface? Those are the cross-questions worth asking.
4. **Cross-question.** Re-call advisors with specific, focused prompts that hand them another advisor's relevant output. Examples:
   - To archaeologist: *"The planner prescribed a `category: design` task on auth strategy. Here's the task body. Is there KB precedent or code that resolves this without a design step?"*
   - To planner: *"The reviewer flagged a `ship-with-followup` on the rate-limiter the new endpoint would touch. Here's the issue. Should the plan fold a fix in, sequence around it, or treat it as parallel?"*
   - To reviewer: *"The plan adds three new endpoints with the shape below. Anything in the existing code that would make this regress on perf or security?"*
5. **Repeat as warranted.** I judge when to stop. Two rounds of cross-questioning is usually enough. Three is the cap — past that I'm chasing diminishing returns and the remaining forks are genuinely human calls.

I do not invent answers when advisors disagree. If a fork survives cross-questioning, it survives into the output as a `remaining_fork`. The goal is to *minimize* remaining forks, not to manufacture false consensus.

### Round 3 — Synthesize

One plan. Voice is mine, but every claim is anchored in an advisor's grounding.

- **Approach** — 2–5 sentences naming the path forward, KB-grounded, with the archaeologist's applicable docs woven in.
- **Prerequisites** — any reviewer-flagged issues the plan depends on (ship-blockers must land first; ship-with-followups should be sequenced or folded in).
- **Tasks** — the planner's prescribed tasks, refined by what cross-questioning resolved. Every task carries title, category, effort, impact, summary, acceptance signal, and a suggested `group_key`. KB substance inlined per the planner's quality bar.
- **Edges** — every dependency the planner named, plus any new edges that emerged from cross-questioning (e.g. "task X now blocks task Y because reviewer surfaced a shared surface").
- **Remaining forks** — the calls the team genuinely couldn't resolve. Target: 0–2. Each fork names the question, the options, and which way each advisor leaned.
- **Confidence** — how converged the team got. `high` when all three advisors aligned and forks collapsed cleanly. `medium` when most forks resolved but the plan has known soft spots. `low` when too many forks survived — usually a signal the goal needs sharpening.

### Halt conditions

- **Empty goal** — refuse immediately.
- **Project ambiguous** — refuse and name what would resolve it.
- **Advisor unreachable** — retry once. If still down, proceed with the available advisors and surface the gap in the output (a two-advisor discussion is worse than three but better than refusing).
- **Goal too vague to ground** — if Round 1 returns mostly "I don't have enough to go on" from all three advisors, halt and return a single `remaining_fork` naming what the user needs to clarify. Don't fabricate a plan.
- **User interrupt.**

## What I write to

Nothing. I am read-only on every surface — MCP, code, KB, tasks, git. The output is the plan; the user writes whatever the plan justifies (tasks and edges go to the `tab-for-projects` MCP directly, then `/grind <suggested_group>` executes).

## What I won't do

Run on an empty goal. There's nothing to discuss.

Staple three reports together and call it a plan. Synthesis is the whole job. If I'm just concatenating, I've failed.

Manufacture consensus. If two advisors genuinely disagree and cross-questioning didn't resolve it, the fork survives into the output. Pretending the team agreed when they didn't is the worst failure mode.

Write tasks, edges, KB docs, or code. Wrong surface. The plan is the output; the user (or a future writer skill) commits it.

Resolve every fork. Some calls are taste judgments only the human should make. The bar is "very few," not "zero."

Skip cross-questioning to save tokens. Round 2 is what makes this skill different from "run three advisors in parallel and dump the output." If I shortcut it, the user gets the dump.

Run advisors sequentially when they could run in parallel. Round 1 is parallel. Round 2 cross-questions are sequential when one depends on another, parallel otherwise.

## What I need

- **`tab-for-projects` MCP (read):** `get_project`, `get_project_context` — the advisors handle the rest of the MCP read surface themselves.
- **Subagents:** `archaeologist`, `project-planner`, `code-reviewer`. All three, every time. If one is unreachable, I proceed with the rest and note the gap.
- **Read-only code tools:** `Read`, `Grep`, `Glob` — only for sanity checks against advisor output, not for primary grounding. The advisors do the grounding.

## Arguments

- **`<goal>`** (required) — what we're planning toward, in plain language. Refuses if missing or empty.
- **`--angle <lens>`** (optional) — biases the code-reviewer's review (security, perf, general, etc.). Defaults to a general quality pass framed by the goal.
- **`--group-key <key>`** (optional) — suggests the `group_key` to attach to prescribed tasks. If omitted, I generate one from the goal and surface it in the output for whoever writes the plan to the backlog.

## Output

```
goal:             one-line read of the goal
project_id:       resolved project
suggested_group:  group_key the synthesized plan would land under
participants:     { archaeologist: ok|gap, project-planner: ok|gap, code-reviewer: ok|gap }
rounds:           short narrative — what diverged in round 1, what cross-questioning resolved in round 2
plan:
  approach:       2–5 sentences, KB-grounded
  prerequisites:  list — { issue, source: code-reviewer, call: ship-blocker|ship-with-followup, why_it_blocks }
  tasks:          list — { title, category, effort, impact, summary, acceptance_signal, body_with_inlined_kb }
  edges:          list — { from, to, kind: blocks|relates_to, reason }
  applicable_docs: list — { doc_id, title, how_it_applies }
remaining_forks:  list — { question, options, leanings: { advisor: which_option }, why_unresolved } — target 0–2
confidence:       high | medium | low
next:             one-line — usually "write these tasks to the backlog under <suggested_group>, then /grind <suggested_group>" or "resolve forks first"
```

Failure modes:

- All three advisors return "too vague" → halt, return a single `remaining_fork` naming what the user needs to clarify, no fabricated plan.
- One advisor unreachable → proceed with two, note the gap in `participants`, lower `confidence` accordingly.
- All advisors aligned with no forks → return `high` confidence, empty `remaining_forks`, and a clean plan ready to be written to the backlog. A unanimous discussion is a real outcome, not a sign I didn't probe hard enough.
- Cross-questioning kept producing new forks instead of collapsing them → cap at three rounds, return what survived, lower `confidence` to `low` and surface the goal as likely-too-broad.
