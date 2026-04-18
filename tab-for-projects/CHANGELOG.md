# Changelog

All notable changes to the **tab-for-projects** plugin. Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow [semver](https://semver.org/).

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
