"""Recall tool wired into the cairn skill's pydantic-ai agent.

The cairn skill is the first CLI-only personality skill (its capability
depends on grimoire-core, which the Claude Code plugin host can't
provide). When activated mid-chat, the SKILL.md body asks the agent to
call the ``recall`` tool, which walks every memory corpus in the
process-wide grimoire DB, gathers the top-similarity neighbours for
the user's query, and returns them as a list of
``{corpus, name, text, similarity}`` rows the model can quote back in
Tab's voice.

Design choices that aren't obvious from the call site:

- **All corpora by default, ``tab-cli-skills`` excluded.** The user
  asked for the search scope to stay open beyond ``topic:*``, so any
  future muse-like accumulator (per-project notes, per-conversation
  summaries) is searched without code change. The skill-routing corpus
  is excluded because its rows are skill *descriptions* authored at
  design time — they're metadata, not Tab thoughts. Surfacing
  "draw-dino: Draw ASCII art dinosaurs" as a recall hit when the user
  asks "what have you thought about creativity" would be a routing
  artefact masquerading as memory. The ``skip_corpora`` argument is
  the override: pass ``frozenset()`` to include everything.
- **Per-corpus :meth:`Gate.explain`, not :meth:`Gate.match`.** ``match``
  filters by each row's per-row threshold, which for ``topic:*`` rows
  was set by ``tab muse`` to its novelty bar (0.7 by default — strict
  enough that "thought is novel" stays meaningful). That bar is the
  wrong question for recall ("is this thought relevant to the
  query?"), so we use ``explain`` and apply our own
  :data:`SIMILARITY_FLOOR` post-filter.
- **Builder + default pair, like :mod:`tab_cli.web_search`.** The
  builder takes injectable seams (``corpus_lister``, ``gate_factory``,
  ``text_lookup``) so tests can drive the tool without grimoire-core
  reachable; :func:`default_recall` constructs the production pair
  against ``grimoire_core``. Same shape the teach skill uses for its
  Exa-backed search tool.
- **Graceful degrade.** If grimoire-core errors out or the DB is empty,
  the tool returns either an empty list (no memories yet) or a single
  ``[recall error]`` row. The cairn SKILL.md treats either case as
  "tell the user there's nothing to draw on" — same fallback shape
  ``web_search`` uses.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any, Protocol


# Cap on results returned to the model. Five is enough for the cairn
# SKILL.md to quote a small handful in Tab's voice without burning
# context on noise; the per-corpus ``TOP_K_PER_CORPUS`` is the upstream
# bound that keeps a single chatty corpus from monopolising the slate.
TOTAL_K = 5

# Per-corpus neighbour limit. Three is a calibration call: enough to
# surface "the well isn't dry on this topic" when one corpus has a
# cluster of related thoughts, but small enough that twenty corpora
# don't drown the cross-corpus sort. Tunable via ``build_recall_tool``.
TOP_K_PER_CORPUS = 3

# Cosine-similarity floor below which a hit isn't surfaced. nomic-
# embed-text puts loosely-related thoughts at ~0.4-0.5 and clearly
# related thoughts at 0.6+; the muse module uses 0.7 for novelty (a
# stricter bar). 0.5 is the recall-shaped middle: generous enough that
# "do you remember thinking about X" finds adjacent thoughts, strict
# enough that an unrelated query returns silence.
SIMILARITY_FLOOR = 0.5

# Corpora to skip by default. ``tab-cli-skills`` is the skill-routing
# corpus — its rows are descriptions of what skills exist, not Tab's
# musings. Surfacing "listen: make space for the user..." as a recall
# hit would conflate routing metadata with memory.
DEFAULT_SKIP_CORPORA = frozenset({"tab-cli-skills"})


class _HitLike(Protocol):
    """Minimal slice of :class:`grimoire_core.Hit` the tool consumes.

    Pinning the surface area as a Protocol keeps test fakes honest —
    a regression that starts touching ``hit.passed`` will fail to
    type-check rather than silently coupling the tool to a wider API.
    """

    name: str
    similarity: float


class _GateLike(Protocol):
    """Minimal slice of :class:`grimoire_core.Gate` the tool consumes."""

    def explain(self, query: str, *, k: int = ...) -> list[_HitLike]: ...


# Tool seams. Three small callables instead of a single big one so
# tests can drive each axis (which corpora exist, what neighbours a
# corpus has, what text a row carries) without re-implementing the
# loop.
CorpusLister = Callable[[], Iterable[str]]
GateFactory = Callable[[str], _GateLike]
TextLookup = Callable[[str, str], str | None]


def _default_corpus_lister() -> Callable[[], Iterable[str]]:
    """Return a lister that walks every corpus grimoire-core knows about.

    Lazy-imports :mod:`grimoire_core` so this module stays cheap to
    import for tests that inject their own seams. Runs migrations
    first via :func:`tab_cli.grimoire_runtime.ensure_migrated`
    (idempotent and process-cached) so a fresh install can recall
    without going through chat / muse first to materialise the
    schema.
    """

    def list_keys() -> Iterable[str]:
        from tab_cli.grimoire_runtime import ensure_migrated

        ensure_migrated()
        from grimoire_core import list_corpora

        return [summary.corpus_key for summary in list_corpora()]

    return list_keys


def _default_gate_factory() -> Callable[[str], _GateLike]:
    """Return a factory that builds a :class:`Gate` per corpus key."""

    def gate_for(corpus: str) -> _GateLike:
        from tab_cli.grimoire_runtime import ensure_migrated

        ensure_migrated()
        from grimoire_core import Gate

        return Gate.from_settings(corpus=corpus)

    return gate_for


def _default_text_lookup() -> Callable[[str, str], str | None]:
    """Return a (corpus, name) -> text lookup using :class:`Curator`.

    Uses :meth:`Curator.get_item` rather than :meth:`Curator.export`
    so we only pay for the row the recall actually surfaced — a
    corpus with hundreds of rows shouldn't materialise all of them
    just to fetch three.

    The Curator is constructed per call rather than cached: process
    lifetime is short (one chat turn between recall invocations), and
    grimoire-core's :meth:`Curator.from_settings` is cheap enough that
    constructing one per row is dominated by the embed/DB cost the
    Gate already paid.
    """

    def lookup(corpus: str, name: str) -> str | None:
        from tab_cli.grimoire_runtime import ensure_migrated

        ensure_migrated()
        from grimoire_core import Curator

        # ``embedder=None`` keeps the curator read/cleanup-only — we
        # never write here, so refusing the embedder construction is
        # a small belt-and-braces against accidental mutation if a
        # bug ever wired write paths into this lookup.
        curator = Curator.from_settings(corpus, embedder=None)
        item = curator.get_item(name)
        return item.text if item is not None else None

    return lookup


def build_recall_tool(
    *,
    corpus_lister: CorpusLister | None = None,
    gate_factory: GateFactory | None = None,
    text_lookup: TextLookup | None = None,
    top_k_per_corpus: int = TOP_K_PER_CORPUS,
    total_k: int = TOTAL_K,
    similarity_floor: float = SIMILARITY_FLOOR,
    skip_corpora: frozenset[str] = DEFAULT_SKIP_CORPORA,
) -> Callable[[str], list[dict[str, Any]]]:
    """Return a ``recall(query)`` callable wired with the given backends.

    The returned callable is what pydantic-ai registers as a tool. Its
    docstring and signature are what the model sees, so they describe
    the tool's *behaviour* and not the runner — "search Tab's memories"
    is what the cairn agent decides to invoke.

    Behaviour:

    - The caller passes ``query``; the tool walks every corpus reported
      by ``corpus_lister`` (minus ``skip_corpora``), runs
      :meth:`_GateLike.explain` per corpus with
      ``k=top_k_per_corpus``, drops hits below ``similarity_floor``,
      looks up the text via ``text_lookup``, and merges the survivors
      into one similarity-sorted list capped at ``total_k``.
    - A row whose ``text_lookup`` returns ``None`` (the corpus has the
      hit's name but the row was deleted between gate and curator
      reads — narrow race) is skipped, not surfaced as an empty
      string. The model would otherwise see a hit with no content
      and have nothing to quote.
    - Any unhandled exception collapses to a single
      ``[recall error]`` row, mirroring :mod:`tab_cli.web_search`'s
      shape. The cairn SKILL.md treats both empty results and error
      rows as "tell the user there's nothing to draw on."
    """
    lister = corpus_lister if corpus_lister is not None else _default_corpus_lister()
    factory = gate_factory if gate_factory is not None else _default_gate_factory()
    lookup = text_lookup if text_lookup is not None else _default_text_lookup()

    def recall(query: str) -> list[dict[str, Any]]:
        """Search Tab's memory corpora for thoughts related to ``query``.

        Returns a list of recall hits, each with ``corpus``, ``name``,
        ``text``, and ``similarity`` keys, sorted by similarity
        descending. The list may be empty when no memory clears the
        relevance floor.

        Args:
            query: A natural-language phrase. Topic-shaped queries
                ("auth rewrite", "the dinosaur conversation") work
                better than abstract ones — embeddings reward
                concrete tokens.
        """
        if not query.strip():
            return []

        try:
            corpora = [c for c in lister() if c not in skip_corpora]
        except Exception as exc:  # noqa: BLE001 — collapse to tool result
            return [_error_row(exc)]

        merged: list[dict[str, Any]] = []
        for corpus in corpora:
            try:
                gate = factory(corpus)
                hits = gate.explain(query, k=top_k_per_corpus)
            except Exception as exc:  # noqa: BLE001 — one bad corpus shouldn't kill the rest
                # Per-corpus failure is recorded as one row so the
                # model knows recall partially succeeded — better
                # than silently dropping a corpus.
                merged.append(_error_row(exc, corpus=corpus))
                continue

            for hit in hits:
                if hit.similarity < similarity_floor:
                    continue
                try:
                    text = lookup(corpus, hit.name)
                except Exception:  # noqa: BLE001 — same corpus-scoped fault tolerance
                    continue
                if text is None:
                    continue
                merged.append(
                    {
                        "corpus": corpus,
                        "name": hit.name,
                        "text": text,
                        "similarity": float(hit.similarity),
                    }
                )

        merged.sort(key=lambda row: row["similarity"], reverse=True)
        return merged[:total_k]

    return recall


def _error_row(exc: Exception, *, corpus: str = "") -> dict[str, Any]:
    """Render a single error-shaped row matching the recall return type.

    Same shape as a real hit so the tool's typed return doesn't fork
    on the error path. Similarity is 0 so the row sorts to the bottom
    if real hits are also present.
    """
    return {
        "corpus": corpus or "[recall error]",
        "name": "",
        "text": f"recall failed: {type(exc).__name__}: {exc}",
        "similarity": 0.0,
    }


def default_recall() -> Callable[[str], list[dict[str, Any]]]:
    """Build the recall tool against the production grimoire-core stack.

    All seams default to the real grimoire-core surface; this is the
    form the chat REPL's grimoire-routed dispatch wraps when it
    routes to the ``cairn`` skill (see ``_tools_for_skill`` in
    :mod:`tab_cli.chat`).
    """
    return build_recall_tool()
