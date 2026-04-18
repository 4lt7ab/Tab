# Changelog

All notable changes to the **tab-for-projects** plugin. Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow [semver](https://semver.org/).

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
