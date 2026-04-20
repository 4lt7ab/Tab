# Changelog

All notable changes to the **tab-for-projects** plugin. Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow [semver](https://semver.org/).

## [0.9.2] — 2026-04-19

### Changed
- `/project` close phase now spells out the full session-close flow: a canonical closing-phrase list (`that's it`, `done for now`, `close out`, `wrap up`, `ship it`, `i'm good`, `that's all`, `let's stop here`, `end session`, and `/close` typed inline) that prompts a single `y` / `not yet` confirm before the recap renders, fresh-topic detection that escalates to the same confirm rather than auto-closing, a `ship it` disambiguation rule that resolves to write-affirmation when the previous turn was a write-confirm and to close otherwise (with a one-line statement of which interpretation the skill took), and a scan-shaped recap template that surfaces task IDs, doc IDs, group routing notes, and a single advisory `Suggest:` line picked from a `/work` > `/backlog` > follow-up `/project` > nothing priority ladder. The recap stays conversation-local — no MCP session record, no session-summary doc by default. The locked copy lives in KB doc `01KPMASNH26NVDP038ZZ1ZDA50` and is quoted verbatim in SKILL.md so close behavior renders consistently across invocations.

## [0.9.1] — 2026-04-19

### Changed
- `/project` no-match branch now spells out the full creation dialog: initial proposal, iterative one-field-at-a-time edit loop with `(changed)` markers on re-confirmation, a 5-edit cap that offers `pick existing` / `cancel` / `keep going` once when the proposal isn't converging, an explicit post-create acknowledgement with no spurious health evaluation, and a `pick existing instead` fallback with an 8-cap `list_projects` search, `back` / `cancel` / re-`search <term>` responses, and no auto-fall-back on empty results or auto-select on a single result. Every write still passes through an explicit `y`; navigational moves do not. The locked copy lives in KB doc `01KPMAFVJ6CDQMGMJRMYDKECAR` and is quoted verbatim in SKILL.md so renderings stay consistent across invocations.

## [0.9.0] — 2026-04-19

### Added
- `/project` — session-oriented planning entry point. Opens on a project (existing or brand-new, with explicit creation confirmation), scores backlog health against the readiness bar once at session open, then hosts an open-ended iteration loop for new initiatives, research threads, decision/convention capture, drive-by task filings, grooming handoffs, and status reads until the user closes. Captures tasks and KB docs as conclusions accumulate — no single end-of-session dump. Research is primary posture (prefers the `exa` MCP, falls back to native web search). Introduces a `team:<team-name>:<initiative-name>` convention on `group_key` for team attribution without an MCP schema change, validated against the 32-char ceiling at confirm time. Cross-references in `/fix`, `/work`, `/search`, `/backlog`, and `/document` updated.

### Removed
- **Breaking:** `/feature` skill. Its capture behavior lives inside `/project`'s iteration loop — a planning session is the natural home for initiative capture, research, and decision documentation, and the "one-shot file" framing pushed the user to dismount between related turns. For single-task drive-by filings from conversation, `/fix` is unchanged. For planning any multi-task work — one initiative or many — invoke `/project` instead.

## [0.8.1] — 2026-04-18

### Changed
- **Breaking:** `/save-document` renamed to `/document`. Matches the noun-shorthand naming the rest of the inventory settled on (`/feature`, `/backlog`, `/search`). Behavior is identical — only the invocation changes. Cross-reference in `/search`'s negative-trigger list updated.

## [0.8.0] — 2026-04-18

### Changed
- `/work` upgraded from a max=5 batched executor to a persistent task-graph walker. The default run now continues until the ready portion of the backlog is empty, the user interrupts, or three consecutive task failures abort — `--max=N` stays as an opt-in safety valve for short runs.
- `/work` now routes each task to the appropriate subagent by category. A new routing table maps all ten categories (feature, bugfix, refactor, test, docs, perf, design, security, infra, chore) to default agents with optional precursor/successor chains (e.g. architect before a medium-effort feature, test-writer after, reviewer after a refactor).
- `/work`'s dispatch contract is now ID-only: subagents receive `task_id`, optional `parent_task_id`, and `group_key` (for shipper) — nothing else. Subagents fetch their own context via the MCP. This keeps the main thread's context window small across long persistent runs.
- Status ceremony (`in_progress` → `done` / `todo`) is owned exclusively by the dispatched subagent. `/work` reads task state after a subagent returns; it never writes task state on the subagent's behalf.
- Halts and newly filed `design`-category tasks are batched into a single end-of-run "needs your call" section — `/work` no longer interrupts mid-run for design questions.
- At end-of-run, `/work` invokes the `shipper` subagent for any `group_key` with unshipped commits, producing PR descriptions / release notes / CHANGELOG polish as drafts. The user still ships — `/work` does not push or merge.
- Parallelism is now opt-in via `--parallel` and only fires within a `group_key` where tasks share no ordering edges and touch different top-level directories. Default is serial.
- End-of-run report expanded: per-task summary with agent name, flagged-below-bar list, needs-your-call section, and shipper output.

## [0.7.0] — 2026-04-18

### Added
- `/feature` now scales rigor to the input instead of relying on a separate skill. A one-line idea with full context still files as one task; a fuzzy multi-surface objective triggers a bounded interview (3–5 questions), targeted web research (when the objective touches unfamiliar territory), and dependency wiring (when the decomposition has natural ordering). The ceiling is full planning; the floor is unchanged — no interview, no research when the conversation already covered it. Picks the right rigor from signals in the input so you don't have to choose up front.

### Removed
- **Breaking:** `/plan-project` skill. Its behavior folded into `/feature` — the planning path (interview + research + decomposition + deps) now activates by signal rather than by invocation. If you were using `/plan-project` to set up a backlog from a fuzzy objective, use `/feature` instead; it will interview and research when needed. Cross-references in `/fix`, `/work`, `/search`, `/backlog`, and `/save-document` were updated.

## [0.6.9] — 2026-04-18

### Changed
- **Breaking:** `/manage-backlog` renamed to `/backlog`. Matches the tight verb-shaped naming of the other skills (`/fix`, `/feature`, `/search`, `/work`). Behavior is identical — only the invocation changes. Cross-references in `/feature`, `/fix`, `/work`, and `/plan-project` were updated.

## [0.6.8] — 2026-04-18

### Removed
- `/get-project` skill. `/search` already covers finding specific docs and tasks, and a full project snapshot that you'd skim but not act on earns its keep less than the skill inventory cost of keeping two entry points for "tell me about this project." If you want a read on where things stand, start a conversation or use `/search`.

## [0.6.7] — 2026-04-17

### Fixed
- `architect` and `docs-writer` subagents now attach produced KB documents to the **project** as the primary linkage, with a breadcrumb reference on the originating task. Previously both prompts instructed the agents to link docs only to the task, which scoped the doc to one unit of work and hid it from the rest of the project. Design docs, upgrade guides, and reference material outlive the tasks that produce them and belong at the project level.

## [0.6.6] — 2026-04-17

### Added
- `shipper` subagent — packages a completed `group_key` into written deliverables: PR description, release notes, or final CHANGELOG polish. Derives the commit range from task ULID references in commit messages, reads linked architect docs for notable-decisions context, and produces prose that stands alone for a reader who wasn't in the conversation. Does not push, merge, or create PRs — the user ships.

## [0.6.5] — 2026-04-17

### Added
- `reviewer` subagent — independent second opinion on a committed diff. Triages findings into critical (reverts task to rework), suggestion (filed as new tasks), and cosmetic (logged only). Does not fix anything; the triage decides what happens next.

## [0.6.4] — 2026-04-17

### Added
- `docs-writer` subagent — produces written artifacts (READMEs, CHANGELOG prose, upgrade guides, inline docs, KB reference material). Has KB-doc authority alongside `architect`. Technical Docs register — structural, precise, low-humor. Source gaps become filed follow-up tasks, not hedged prose.

## [0.6.3] — 2026-04-17

### Added
- `test-writer` subagent — produces tests for an implementation without modifying it. Pins current observable behavior; when it notices the behavior looks wrong, writes the test anyway (capturing reality) and files a new bugfix task rather than silently correcting the code. Tests-only mandate.

## [0.6.2] — 2026-04-17

### Changed
- Renamed `developer` agent to `implementer` and adapted the prompt to the autonomous ID-only contract shared by the new subagent roster. Dispatch shape simplified from `{ task_ids[], project_id, worktree? }` to `{ task_id, parent_task_id? }` — one task per invocation, MCP is the source of truth, the caller owns the loop.
- Filing authority made explicit: `implementer` may create new tasks for follow-up work surfaced during implementation but may not create or modify KB documents. The knowledgebase is reserved for `architect` and (upcoming) `docs-writer`.

## [0.6.1] — 2026-04-17

### Added
- `architect` subagent — produces design documents, ADRs, and implementation plans for design-category tasks or feature tasks heavy enough to warrant an up-front design pass. Writes documents to the KB, links them to the originating task, and files follow-up design tasks for any forks it couldn't resolve from context. Does not write source code.

## [0.6.0] — 2026-04-17

### Changed
- **Breaking:** `/develop` renamed to `/work`. Behavior is identical; the persistent-loop + agent-routing upgrade lands in a follow-up. Cross-references in `/manage-backlog`, `/plan-project`, `/fix`, `/get-project`, and the `developer` agent were updated to match. The Task Readiness Bar convention doc was updated in the KB.

## [0.5.0] — 2026-04-17

### Added
- `/feature` — sibling of `/fix` for capturing new feature ideas onto the backlog. Accepts user-supplied context only (no codebase search, no web research, no interview), shapes it into 1 or more tasks above the readiness bar, confirms once, and writes. Use it when an idea deserves a task but doesn't justify a `/plan-project` session.

## [0.4.0] — current

Changelog maintenance starts at this version. See git history for changes in earlier releases.
