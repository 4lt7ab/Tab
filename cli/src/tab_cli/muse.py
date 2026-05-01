"""Topic-keyed thinking loop: Tab curates his own grimoire about a topic.

The shape: pick a topic, generate one Tab-voiced thought at a time,
embed-and-gate each thought against a topic-specific grimoire corpus,
keep what's novel and skip what's redundant. Stop on convergence
(``stale_limit`` consecutive redundant thoughts) or budget exhaustion.

The corpus key is ``topic:<slug>``. It persists across sessions —
yesterday's thoughts still gate today's via ``Gate.match``. The
in-prompt "things you've already said" context, however, is
session-local: we don't read prior-session rows back into the prompt.
(``Curator.export`` would surface them, but pulling rows we'd just
re-show the model risks re-priming it on its own past output rather
than letting it generate fresh.) That's fine: the model may propose
a thought already in the corpus from a prior session, the gate
catches it, the stale-streak ticks up, the loop terminates exactly
as intended.

Why a separate corpus per topic: grimoire's silence-by-default
semantics work corpus-wide. One mega-corpus would mean a thought
about auth could bump a thought about onboarding off the top-1, and
"already covered" would lose meaning. Per-topic keeps the novelty
question scoped to the topic.

Auto-row-naming: each new row is ``thought-<N>`` where N is its order
in the corpus across all sessions (the loop reads the existing row
count once at startup via ``Curator.export`` and offsets from there).
Names must be unique within a corpus — ``Curator.add_item`` raises
``ItemAlreadyExists`` on a clash — and the loop doesn't have a
richer label to hang on the row, since the *content* is the
description (what gets embedded). For diagnostics ("matches
thought-3, sim 0.74"), a short numeric tag is more legible than a
hash.
"""

from __future__ import annotations

import re
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import IO, TYPE_CHECKING

if TYPE_CHECKING:
    from grimoire_core import Curator, Gate
    from pydantic_ai import Agent

    from tab_cli.personality import TabSettings


# Defaults — picked by feel, not calibration. The whole loop's
# behaviour is sensitive to these three numbers and we'll need real
# topic runs to tune them. Documenting the guess so the next person to
# touch this knows what assumption is on the table:
#
# * BUDGET 15: enough for the model to get past obvious takes and
#   surface something interesting; small enough that a botched run
#   doesn't burn a wallet.
# * STALE_LIMIT 3: one redundant thought is noise (the model had a
#   weak turn), two is a coincidence, three in a row reads as the
#   well actually being dry.
# * NOVELTY_THRESHOLD 0.7: nomic-embed-text puts paraphrases at 0.75+
#   and semantically distinct thoughts under 0.6 in our existing
#   skill-routing calibration. 0.7 is the gap.
DEFAULT_BUDGET = 15
DEFAULT_STALE_LIMIT = 3
DEFAULT_NOVELTY_THRESHOLD = 0.7


@dataclass(frozen=True, slots=True)
class Thought:
    """One accepted thought added to the corpus this session.

    ``index`` is the row's order in the corpus *across all sessions*,
    not within this run. It is also encoded into the auto-generated
    row name (``thought-<index>``) so a diagnostic line ("matches
    thought-3, sim 0.74") can be cross-referenced against the corpus
    without a separate lookup, and so that session 2's writes don't
    collide with session 1's row names.
    """

    index: int
    text: str


@dataclass(frozen=True, slots=True)
class RedundantThought:
    """One thought rejected by the novelty gate.

    Carries the gate's :class:`grimoire_core.Hit` data verbatim — the
    matched row name and similarity — so the loop can render
    "matches thought-3, sim 0.74" and the caller can audit *why* the
    gate said redundant.
    """

    text: str
    similarity: float
    matched_name: str


@dataclass
class _MuseSession:
    """Mutable per-session state for the muse loop.

    Bundled so the loop body passes one object instead of half a dozen
    scalars. Mirrors the shape of :class:`tab_cli.chat._Session` on
    purpose — both are short-lived REPL-shaped state holders.

    Holds both halves of grimoire-core's split surface: ``gate`` for
    the per-iteration ``match`` call, ``curator`` for adding the
    accepted thought back into the corpus.
    """

    agent: Agent
    gate: Gate
    curator: Curator
    topic: str
    # Count of rows already in the corpus at session start. Folded
    # into the auto-generated row name so session 2's first thought is
    # ``thought-<N+1>`` rather than ``thought-1`` — ``Curator.add_item``
    # raises ``ItemAlreadyExists`` on a name clash, and the loop's
    # whole point is *additive* corpus building across sessions.
    base_index: int = 0
    accepted: list[Thought] = field(default_factory=list)
    stale_streak: int = 0


def slugify_topic(topic: str) -> str:
    """Turn a free-form topic into a corpus-key-safe slug.

    Lowercases, collapses runs of non-alphanumerics to single hyphens,
    strips leading/trailing hyphens. Empty slugs (e.g. all-punctuation
    input) fall back to ``"untitled"`` rather than producing a
    corpus-key like ``topic:`` which grimoire would likely reject and
    which silently aliases every topic-less call to the same corpus.
    """
    lower = topic.strip().lower()
    hyphenated = re.sub(r"[^a-z0-9]+", "-", lower).strip("-")
    return hyphenated or "untitled"


def corpus_key(topic: str) -> str:
    """Compose the grimoire corpus key for ``topic``.

    The ``topic:`` prefix namespaces muse corpora away from the
    skill-routing corpus (``tab-cli-skills``). A future ``tab muse
    list`` would filter by this prefix.
    """
    return f"topic:{slugify_topic(topic)}"


def _build_prompt(topic: str, prior: list[Thought]) -> str:
    """Render the per-iteration user prompt.

    The "no preface, no boilerplate" line is load-bearing: without it
    models reliably emit "Here's another thought:" / "One more
    thing:" prefixes that share embedding space and inflate similarity
    against past entries — the gate then rejects everything as
    redundant on surface form alone.
    """
    if not prior:
        return (
            f"Topic: {topic}\n\n"
            "Generate ONE new thought about this topic. "
            "A single sentence. No preface, no boilerplate. Just the thought."
        )
    bullets = "\n".join(f"- {t.text}" for t in prior)
    return (
        f"Topic: {topic}\n\n"
        f"Things you've already said:\n{bullets}\n\n"
        "Generate ONE new thought about this topic that is genuinely "
        "different from what you've already said. A single sentence. "
        "No preface, no boilerplate. Just the thought."
    )


# Type for the callback that renders each iteration's outcome to the
# user. Default is :func:`_default_renderer` (writes to stdout); tests
# inject a list-collecting callback instead. Splitting render from
# loop keeps the loop body free of formatting decisions.
Renderer = Callable[[int, "Thought | RedundantThought"], None]


def _default_renderer(out: IO[str]) -> Renderer:
    """Build the stdout renderer. One line per outcome, plus status."""

    def render(iteration: int, outcome: Thought | RedundantThought) -> None:
        if isinstance(outcome, Thought):
            out.write(f"[{iteration}] {outcome.text}\n    + new\n")
        else:
            out.write(
                f"[{iteration}] {outcome.text}\n"
                f"    - redundant (matches {outcome.matched_name}, "
                f"sim {outcome.similarity:.2f})\n"
            )
        out.flush()

    return render


def run_muse(
    topic: str,
    *,
    settings: TabSettings | None = None,
    model: str | None = None,
    budget: int = DEFAULT_BUDGET,
    stale_limit: int = DEFAULT_STALE_LIMIT,
    novelty_threshold: float = DEFAULT_NOVELTY_THRESHOLD,
    stdout: IO[str] | None = None,
    gate: Gate | None = None,
    curator: Curator | None = None,
) -> list[Thought]:
    """Run the muse loop against ``topic``, returning accepted thoughts.

    Each iteration:

    1. Build a prompt with this-session prior thoughts.
    2. Generate one sentence via the Tab-personality agent.
    3. ``gate.match`` the sentence against the topic corpus. The new
       grimoire-core surface returns only passed hits, so a non-empty
       result already means "redundant".
    4. If a hit was returned → redundant; skip and increment
       ``stale_streak``.
    5. Otherwise → ``curator.add_item`` the new row at
       ``novelty_threshold``, reset ``stale_streak``, append to
       ``accepted``.

    The loop terminates when ``stale_streak >= stale_limit`` (the well
    is dry) or ``budget`` iterations have run.

    ``gate=`` and ``curator=`` are paired test seams — production
    callers omit both and the function constructs the canonical pair
    via ``Gate.from_settings`` / ``Curator.from_settings`` keyed on
    the same ``corpus_key(topic)``. Mirrors the same keyword-only
    override pattern :func:`tab_cli.registry.load_skill_registry`
    uses.
    """
    # Lazy imports keep the muse module cheap to load when ``tab --help``
    # or unrelated subcommands run. Same pattern as
    # :mod:`tab_cli.chat` and :mod:`tab_cli.skills`.
    from grimoire_core import Curator as _Curator
    from grimoire_core import Gate as _Gate

    from tab_cli.personality import TabSettings, compile_tab_agent

    out = stdout if stdout is not None else sys.stdout
    active_settings = settings if settings is not None else TabSettings()
    agent = compile_tab_agent(settings=active_settings, model=model)

    key = corpus_key(topic)
    if gate is None or curator is None:
        # Run pending grimoire migrations before constructing anything
        # settings-backed, so the schema is in place by the time the
        # first ``match`` / ``add_item`` lands. Cached at process scope,
        # so a chat session that already migrated via the registry
        # path falls through here with no DB touch.
        from tab_cli.grimoire_runtime import ensure_migrated

        ensure_migrated()
    if gate is None:
        gate = _Gate.from_settings(corpus=key)
    if curator is None:
        curator = _Curator.from_settings(corpus=key)

    # One ``export`` at session start gives us the count of prior-session
    # rows so we can offset our auto-naming. Empty list when the corpus
    # has never been written; that's the first-ever-run case and base
    # stays at 0.
    base_index = len(curator.export())

    session = _MuseSession(
        agent=agent,
        gate=gate,
        curator=curator,
        topic=topic,
        base_index=base_index,
    )
    render = _default_renderer(out)

    out.write(f"Tab is musing on: {topic}\n\n")
    out.flush()

    terminated_by_stale = False
    for iteration in range(1, budget + 1):
        if session.stale_streak >= stale_limit:
            terminated_by_stale = True
            break

        prompt = _build_prompt(session.topic, session.accepted)
        result = session.agent.run_sync(prompt)
        thought_text = result.output.strip()

        hits = session.gate.match(thought_text)
        if hits:
            hit = hits[0]
            session.stale_streak += 1
            render(
                iteration,
                RedundantThought(
                    text=thought_text,
                    similarity=hit.similarity,
                    matched_name=hit.name,
                ),
            )
            continue

        next_index = session.base_index + len(session.accepted) + 1
        row_name = f"thought-{next_index}"
        # ``add_item`` rather than ``seed``: ``seed`` wipes-and-rewrites
        # the corpus, which would erase yesterday's thoughts on every
        # new one we accept. ``add_item`` is the per-row write that
        # preserves prior session state.
        session.curator.add_item(row_name, thought_text, novelty_threshold)
        thought = Thought(index=next_index, text=thought_text)
        session.accepted.append(thought)
        session.stale_streak = 0
        render(iteration, thought)

    if terminated_by_stale:
        out.write(f"\n— stale-streak {stale_limit} reached, the well's run dry.\n")
    else:
        out.write(f"\n— budget {budget} exhausted.\n")
    out.write(
        f"Added {len(session.accepted)} thought(s) to {corpus_key(topic)}.\n"
    )
    out.flush()
    return session.accepted
