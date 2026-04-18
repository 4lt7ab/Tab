# Changelog

All notable changes to the **tab-for-projects** plugin. Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow [semver](https://semver.org/).

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
