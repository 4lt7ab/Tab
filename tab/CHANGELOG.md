# Changelog

All notable changes to the **tab** plugin. Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow [semver](https://semver.org/).

## [0.2.2] — 2026-04-17

### Added
- `/teach` now disambiguates vague topics before researching. `/teach AI`, `/teach databases`, or `/teach performance` used to send the research subagent chasing an umbrella term; now Tab asks which corner you're actually after — one question, then into the normal flow.

## [0.2.1] — 2026-04-17

### Changed
- `/teach` syllabus entries now carry **type** and **difficulty** alongside search terms, so the skill can group topics when a user wants to browse what's available instead of naming a topic. All 38 existing entries backfilled; new entries must set both fields.

## [0.2.0] — 2026-04-16

### Changed
- `/hey-tab` now installs the Exa MCP at `--scope user` instead of the default project scope, so it's available across all projects after a single setup.
- `/teach` syllabus expanded from 12 to 38 entries. New coverage:
  - Operational patterns: caching strategies, idempotency, schema migrations, observability, feature flags.
  - Mental models: Chesterton's fence, Goodhart's law, Conway's law, pre-mortems.
  - Underused technical primitives: finite state machines, merkle trees, choose boring technology, cargo cult programming, theory of constraints.
  - AI literacy: how LLMs work, tokenization, context windows, embeddings, prompt engineering, hallucination, fine-tuning vs prompting vs RAG, reasoning models.
  - Practitioner AI topics: RAG, LLM evals, agent loops.
  - Stack-specific: React + Vite + Bun web apps.

## Prior versions

Earlier releases (≤ 0.1.x) predate this changelog. See git history for details.
