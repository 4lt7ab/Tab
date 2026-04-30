---
description: Opinionated review — at most 3 feature suggestions for Tab, every claim earns its keep.
---

You are reviewing the Tab repository and returning **at most three** opinionated suggestions for feature additions or improvements. Fewer is better than more. Zero is a valid answer if nothing meets the bar.

## What Tab is

Read `CLAUDE.md` first; it's the architectural ground truth. The substrate is markdown — skills under `plugins/tab/skills/*/SKILL.md`, the personality agent at `plugins/tab/agents/tab.md`, both consumed by two interchangeable runtimes: the Claude Code plugin and a Python CLI under `cli/`.

Before forming any opinion, scan:

- `README.md`, `CLAUDE.md` — voice, scope, decisions already rejected (the "Decisions we rejected" section is binding — don't re-pitch them)
- `plugins/tab/agents/tab.md` — the five personality dials and the agent body
- Every `plugins/tab/skills/*/SKILL.md` — the shipped skills (today: `draw-dino`, `hey-tab`, `listen`, `teach`, `think`)
- `cli/src/tab_cli/cli.py` and `cli/MAINTENANCE.md` — the CLI surface
- `cli/src/tab_cli/registry.py`, `personality.py`, `models/ollama_native.py` — runtime seams
- `scripts/validate-plugins.sh` — what's currently enforced
- Recent `git log --oneline -30` — the trajectory

## The bar

Every suggestion must clear all of these:

1. **Names a concrete user or developer outcome.** "Improve DX" is not an outcome. "Let users persist personality dial defaults so they stop re-flagging every invocation" is.
2. **Cites the file(s) it would touch.** If you can't point at the seam, you don't understand the change.
3. **Is grounded in something you read, not pattern-matched from generic advice.** No "add tests," "add CI," "add docs" unless you found a specific gap with a specific cost.
4. **Is consistent with rejected decisions in CLAUDE.md.** Don't re-pitch `tab mcp`, frontmatter expansion, vendored markdown, or a stock `OllamaModel` swap.
5. **Fits Tab's voice.** Tab is terse, opinionated, magical-cottagecore-craftsman. Suggestions that bloat the surface, add ceremony, or dilute the personality fail this even if technically sound.

Reject in advance: enterprise checklist items (monitoring, telemetry, plugin marketplaces, multi-tenancy), generic refactors with no named payoff, "consider adding X" framed as optionality, anything that reads as content-for-content's-sake.

## Output shape

For each suggestion (max 3), write:

**Title** — one line, imperative, under ~10 words.

- **What:** 1–2 sentences. The change.
- **Why it earns its keep:** 1–2 sentences. The specific cost being paid today, or the specific capability missing. Cite a file path or behavior.
- **Where it lives:** the file(s) or seam touched.
- **Cost / risk:** one line. Be honest if it's a substrate-shape change vs. a contained tweak.

If only one suggestion clears the bar, return one. If none do, say so in a single sentence and stop. Don't pad.

## Tone

Match Tab's voice: direct, terse, willing to disagree with the codebase. No hedging, no "you might consider," no exec-summary preamble. Lead with the recommendation.
