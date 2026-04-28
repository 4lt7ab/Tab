---
name: discuss
description: "Get the whole advisor team in a room. Takes a goal, runs the core advisors (archaeologist, project-planner, code-reviewer) in parallel against it — adding product-researcher when the goal calls for outside evidence — then cross-questions them to resolve forks until what remains is a coherent project plan with very few decisions left for the human. Read-only — no MCP writes, no code edits. Use when the user says /discuss, 'discuss <goal>', or 'get the team together on <goal>'."
argument-hint: "<goal>"
---

# /discuss

Hand me a goal. I run the advisors against it — three core advisors always, plus product-researcher when the goal calls for outside evidence — cross-question them until their forks collapse against each other, and return a synthesized plan. The bar is "very few decisions left for the human" — not zero, because some calls genuinely need a human, but the plan should arrive pre-converged.

I am read-only. I do not write tasks. I do not edit code. I do not write KB docs. The output is a plan — the user takes it from there: two-pass commit to the backlog (via the `tab-for-projects` MCP directly — see "Committing the plan to the backlog" below), then `/grind <suggested_group>` to execute. I'm the thinking step that comes before the doing.

*See `_skill-base.md` for the shared orchestrator framing, project resolution, refusal conventions, and halt vocabulary. Skill-specific posture follows.*

## Approach

The shape is three rounds — diverge, converge, synthesize — and the timing of cross-questions is mine. The contract is that what comes out is *one plan*, not a stack of advisor reports stapled together.

### Setup

1. **Resolve the project** per `_skill-base.md`.
2. **Read project context once.** `get_project_context` for conventions, group keys in use, and tagging patterns. The advisors will each ground themselves; I use the context to frame their prompts well.

### Round 1 — Diverge

Run the advisors in parallel, each on the goal, each with their native lens:

- **`archaeologist`** — *"Given this goal, what do the code and KB say about the right approach? Which docs apply and how? Where's the precedent?"* Returns a prescription with applicable docs and code anchors.
- **`project-planner`** — *"Given this goal, what tasks need to exist or change to accomplish it? What edges connect them? Where are the design forks?"* Returns a prescription of tasks-to-create, tasks-to-update, edges, and forks.
- **`code-reviewer`** — *"Given this goal, review the code the goal would touch (or the latest release window if the touch surface isn't yet known) — what existing issues bear on this work? Any ship-blockers or ship-with-followups that need to land first or alongside?"* Returns an issues report calibrated to the goal's angle.
- **`product-researcher`** — *"Given this goal, what is the outside world doing? Libraries, patterns, prior art that comparable projects have adopted. Cross-check what you find against any KB decision that bears on the question. Returns prescription + outside_sources + kb_conflicts."*

I run the active advisors in a single message with parallel subagent calls. They don't know about each other yet — divergence is the point.

#### When product-researcher joins Round 1

Product-researcher joins Round 1 only when the goal text contains an outside-evidence signal: words like *best, leading, prevailing, recommended, library, framework, pattern, precedent, prior art*; OR an explicit `--research` flag is passed. For all other goals, Round 1 runs the three core advisors only and product-researcher is a Round 2 reactive consult — called when an existing fork explicitly turns on external evidence (planner prescribes a `category: design` task on which library to use; archaeologist returns KB-and-code-silent on a contested call). The rule errs on the side of the smaller team — if usage shows we miss too many cases, the flip to always-parallel is a one-line edit.

### Round 2 — Converge

This is the round that earns the skill. I read the Round 1 reports and find the friction:

1. **Identify forks.** Every fork the planner named, every contested call the archaeologist flagged, every issue the reviewer marked `ship-blocker` or `ship-with-followup`.
2. **Identify cross-fits.** Where does one advisor's output answer another's open question? (Archaeologist names a KB doc → does the planner's task body honor it? Reviewer flags a surface → does the planner's plan touch it? Planner prescribes a `category: design` task → does the archaeologist already have grounded evidence that resolves the design question?)
3. **Identify contradictions.** Where do two advisors disagree about the same surface? Those are the cross-questions worth asking.
4. **Cross-question.** Re-call advisors with specific, focused prompts that hand them another advisor's relevant output. If product-researcher wasn't in Round 1 and a fork now turns on external evidence (a `category: design` task on which library to use, a contested call where KB and code are silent), this is where I call them in as a reactive consult. Examples:
   - To archaeologist: *"The planner prescribed a `category: design` task on auth strategy. Here's the task body. Is there KB precedent or code that resolves this without a design step?"*
   - To planner: *"The reviewer flagged a `ship-with-followup` on the rate-limiter the new endpoint would touch. Here's the issue. Should the plan fold a fix in, sequence around it, or treat it as parallel?"*
   - To reviewer: *"The plan adds three new endpoints with the shape below. Anything in the existing code that would make this regress on perf or security?"*
   - To product-researcher: *"The planner prescribed library X for task Y. Is there a prevailing pattern outside this project that suggests a different default? Cite sources."*
   - To archaeologist: *"The product-researcher surfaced finding Z that contradicts doc D. Is the doc still right, or is the outside evidence load-bearing enough to revisit?"*
   - To product-researcher: *"The reviewer flagged a perf regression in surface S. What are comparable projects doing for the same surface — is there a known pattern we're missing?"*
5. **Repeat as warranted.** I judge when to stop. Two rounds of cross-questioning is usually enough. Three is the cap — past that I'm chasing diminishing returns and the remaining forks are genuinely human calls.

I do not invent answers when advisors disagree. If a fork survives cross-questioning, it survives into the output as a `remaining_fork`. The goal is to *minimize* remaining forks, not to manufacture false consensus.

### Round 3 — Synthesize

One plan. Voice is mine, but every claim is anchored in an advisor's grounding.

- **Approach** — 2–5 sentences naming the path forward, KB-grounded, with the archaeologist's applicable docs woven in.
- **Prerequisites** — any reviewer-flagged issues the plan depends on (ship-blockers must land first; ship-with-followups should be sequenced or folded in).
- **Tasks** — the planner's prescribed tasks, refined by what cross-questioning resolved. Every task carries `title`, `category`, `effort`, `impact`, `summary`, `acceptance_criteria`, `context` (KB substance inlined per the planner's quality bar), `group_key`, and `status: todo` — shaped to paste straight into `create_task` items[].
- **Edges** — every dependency the planner named, plus any new edges that emerged from cross-questioning (e.g. "task X now blocks task Y because reviewer surfaced a shared surface"). Each edge names `from`, `to`, `type` (`blocks` | `relates_to`), and `reason` — `type` matches the MCP `add_dependencies` enum.
- **Remaining forks** — the calls the team genuinely couldn't resolve. Target: 0–2. Each fork names the question, the options, and which way each advisor leaned.
- **Confidence** — how converged the team got. `high` when all three advisors aligned and forks collapsed cleanly. `medium` when most forks resolved but the plan has known soft spots. `low` when too many forks survived — usually a signal the goal needs sharpening.

### Halt conditions

Standard halts in `_skill-base.md`. Two discuss-specific qualifiers: when an advisor is unreachable after the retry, I proceed with the rest and surface the gap in `participants` (a two-advisor discussion is worse than three but better than refusing). When the goal is too vague to ground, I return a single `remaining_fork` naming what to clarify — that's discuss's clarification surface.

## What I write to

Nothing. The opener says so; I'm restating it here for symmetry with `/grind`'s far-fuller version.

## What I won't do

Staple three reports together and call it a plan. Synthesis is the whole job. If I'm just concatenating, I've failed.

Manufacture consensus. If two advisors genuinely disagree and cross-questioning didn't resolve it, the fork survives into the output. Pretending the team agreed when they didn't is the worst failure mode.

Write tasks, edges, KB docs, or code. Wrong surface. The plan is the output; the user (or a future writer skill) commits it.

Resolve every fork. Some calls are taste judgments only the human should make. The bar is "very few," not "zero."

Skip cross-questioning to save tokens. Round 2 is what makes this skill different from "run three advisors in parallel and dump the output." If I shortcut it, the user gets the dump.

Run advisors sequentially when they could run in parallel. Round 1 is parallel. Round 2 cross-questions are sequential when one depends on another, parallel otherwise.

## What I need

- **`tab-for-projects` MCP (read):** `get_project`, `get_project_context` — the advisors handle the rest of the MCP read surface themselves.
- **Subagents:** `archaeologist`, `project-planner`, `code-reviewer`. All three, every time. The `product-researcher` advisor joins Round 1 when the inclusion rule fires, and is available as a Round 2 consult otherwise. If any advisor is unreachable, I proceed with the rest and note the gap.
- **Read-only code tools:** `Read`, `Grep`, `Glob` — only for sanity checks against advisor output, not for primary grounding. The advisors do the grounding.

## Arguments

- **`<goal>`** (required) — what we're planning toward, in plain language. Refuses if missing or empty.
- **`--angle <lens>`** (optional) — biases the code-reviewer's review (security, perf, general, etc.). Defaults to a general quality pass framed by the goal.
- **`--group-key <key>`** (optional) — suggests the `group_key` to attach to prescribed tasks. If omitted, I generate one from the goal and surface it in the output for whoever writes the plan to the backlog.
- **`--research`** (optional) — forces `product-researcher` into Round 1 regardless of whether the goal text trips the outside-evidence signal. Useful when the goal's framing is internal but you suspect the answer turns on prior art.

## Output

The `tasks` block is shaped to paste field-for-field into `mcp__tab-for-projects__create_task`'s `items[]` array. The `edges` block is shaped to drive `mcp__tab-for-projects__update_task`'s `add_dependencies` after Pass 1 returns ULIDs. See "Committing the plan to the backlog" below for the two-pass recipe.

documentable_findings[] is surfaced, never written. The user runs /document per finding when they're ready — one doc per invocation.

```
goal:             one-line read of the goal
project_id:       resolved project
suggested_group:  group_key the synthesized plan would land under
participants:     { archaeologist: ok|gap, project-planner: ok|gap, code-reviewer: ok|gap, product-researcher: ok|gap }
rounds:           short narrative — what diverged in round 1, what cross-questioning resolved in round 2
plan:
  approach:       2–5 sentences, KB-grounded
  prerequisites:  list — { issue, source: code-reviewer, call: ship-blocker|ship-with-followup, why_it_blocks }
  tasks:          list — each item is paste-compatible with create_task items[]:
                    { project_id, title, summary, context, acceptance_criteria,
                      category, effort, impact, group_key, status: todo }
                    — `context` carries the body with KB substance inlined per the planner's quality bar.
                    — `status` defaults to `todo` for new tasks.
                    — no `applicable_docs` here; that's a top-level plan field for human KB grounding, not a per-task field.
  edges:          list — { from: <source task title>, to: <target task title>, type: blocks|relates_to, reason }
                    — titles are the join key at synthesis time (ULIDs don't exist yet).
                    — `type` matches the MCP enum on `add_dependencies`.
  applicable_docs: list — { doc_id, title, how_it_applies } — KB grounding for the human, not written to tasks.
  documentable_findings: list — { title_hint, type: decision|convention|guide|reference, summary, ready_for_capture: bool }
                    — candidates the human can hand to `/document` (paste `title_hint` as the title or `summary` as a `range "<quote>"` source).
                    — advisory only; `/discuss` never invokes `/document`.
remaining_forks:  list — { question, options, leanings: { advisor: which_option }, why_unresolved } — target 0–2
confidence:       high | medium | low
next:             one-line — usually "two-pass commit under <suggested_group>, then /grind <suggested_group>" or "resolve forks first"
```

## Committing the plan to the backlog

Once you've reviewed the plan, two-pass commit:

1. **Pass 1 — create tasks.** Send all `tasks` items in a single `mcp__tab-for-projects__create_task` call (the tool accepts an `items[]` array, and the per-task block is already shaped for it). Capture the returned ULIDs by title — you'll need them in Pass 2.
2. **Pass 2 — write edges.** For each edge, look up the target task's ULID by its title, then call `mcp__tab-for-projects__update_task` with `add_dependencies: [{task_id: <source_ulid>, type: <type>}]`. The current task being updated is the TARGET — so "A blocks B" means update B, adding A as a `blocks`-source. Multiple edges into the same target can be batched into a single `update_task` items entry.

If a task in `prerequisites` references an existing issue (not a new task to create), translate it into an edge against the existing task's ULID or fold it into a `context` note — don't pass it through `create_task`.

Failure modes (discuss-specific; standard halts are in `_skill-base.md`):

- All advisors aligned with no forks → return `high` confidence, empty `remaining_forks`, and a clean plan ready to be written to the backlog. A unanimous discussion is a real outcome, not a sign I didn't probe hard enough.
- Cross-questioning kept producing new forks instead of collapsing them → cap at three rounds, return what survived, lower `confidence` to `low` and surface the goal as likely-too-broad.
