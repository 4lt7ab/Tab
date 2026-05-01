"""Tests for :mod:`tab_cli.recall` — the cairn skill's memory tool.

The contract pinned here is narrow but load-bearing. The cairn SKILL
body trusts the tool to either return memory-shaped rows
(``[{corpus, name, text, similarity}]``) or to degrade quietly when
grimoire is unreachable. A regression in either direction breaks the
SKILL's recall phase silently — the model would either drop the
shape it expects to consume, or surface a transport exception that
the SKILL doesn't know how to recover from.

The grimoire path is exercised via injectable seams (``corpus_lister``,
``gate_factory``, ``text_lookup``) rather than a real DB / Ollama
stack — same shape :mod:`tab_cli.web_search`'s tests use, and same
reason: the surface area is tiny and a stub keeps the suite hermetic.
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from tab_cli.recall import (
    DEFAULT_SKIP_CORPORA,
    SIMILARITY_FLOOR,
    build_recall_tool,
)


# --------------------------------------------------------------- fakes


@dataclass
class _FakeHit:
    """Stand-in for :class:`grimoire_core.Hit` — only the fields the tool reads."""

    name: str
    similarity: float


class _FakeGate:
    """Returns canned hits for a corpus key. Records every ``explain`` call."""

    def __init__(self, hits: list[_FakeHit]) -> None:
        self.hits = hits
        self.calls: list[tuple[str, int]] = []

    def explain(self, query: str, *, k: int = 5) -> list[_FakeHit]:
        self.calls.append((query, k))
        return list(self.hits)


def _make_tool(
    *,
    corpora: dict[str, list[_FakeHit]],
    texts: dict[tuple[str, str], str],
    similarity_floor: float = SIMILARITY_FLOOR,
    top_k_per_corpus: int = 3,
    total_k: int = 5,
    skip_corpora: frozenset[str] = DEFAULT_SKIP_CORPORA,
):
    """Build a recall tool with the given canned corpora + texts.

    Centralising the wiring keeps each test focused on a single
    behaviour — the seam construction is the same boring shape every
    time.
    """
    gates = {key: _FakeGate(hits) for key, hits in corpora.items()}

    def lister():
        return list(corpora.keys())

    def factory(corpus: str) -> _FakeGate:
        return gates[corpus]

    def lookup(corpus: str, name: str) -> str | None:
        return texts.get((corpus, name))

    return (
        build_recall_tool(
            corpus_lister=lister,
            gate_factory=factory,
            text_lookup=lookup,
            similarity_floor=similarity_floor,
            top_k_per_corpus=top_k_per_corpus,
            total_k=total_k,
            skip_corpora=skip_corpora,
        ),
        gates,
    )


# ------------------------------------------------------------- happy path


def test_recall_returns_rows_sorted_by_similarity_desc() -> None:
    recall, _ = _make_tool(
        corpora={
            "topic:auth": [_FakeHit("thought-1", 0.62), _FakeHit("thought-2", 0.91)],
            "topic:ux": [_FakeHit("thought-3", 0.78)],
        },
        texts={
            ("topic:auth", "thought-1"): "first auth thought",
            ("topic:auth", "thought-2"): "second auth thought",
            ("topic:ux", "thought-3"): "ux thought",
        },
    )

    rows = recall("anything")

    assert [row["similarity"] for row in rows] == [0.91, 0.78, 0.62]
    assert rows[0] == {
        "corpus": "topic:auth",
        "name": "thought-2",
        "text": "second auth thought",
        "similarity": 0.91,
    }


def test_recall_filters_below_similarity_floor() -> None:
    recall, _ = _make_tool(
        corpora={
            "topic:auth": [
                _FakeHit("clear", 0.71),
                _FakeHit("blurred", 0.42),  # below 0.5 default
            ],
        },
        texts={
            ("topic:auth", "clear"): "passes the floor",
            ("topic:auth", "blurred"): "should be dropped",
        },
    )

    rows = recall("query")

    names = [row["name"] for row in rows]
    assert names == ["clear"]


def test_recall_caps_at_total_k() -> None:
    recall, _ = _make_tool(
        corpora={
            f"topic:c{i}": [_FakeHit(f"hit-{i}", 0.9 - 0.01 * i)] for i in range(8)
        },
        texts={(f"topic:c{i}", f"hit-{i}"): f"text {i}" for i in range(8)},
        total_k=5,
    )

    rows = recall("query")

    assert len(rows) == 5
    # The five highest similarities are 0.90, 0.89, 0.88, 0.87, 0.86.
    assert [round(r["similarity"], 2) for r in rows] == [0.90, 0.89, 0.88, 0.87, 0.86]


# ---------------------------------------------------------- skip / scope


def test_recall_skips_default_corpora() -> None:
    """``tab-cli-skills`` is metadata, not memory — never surfaced by default."""
    recall, gates = _make_tool(
        corpora={
            "tab-cli-skills": [_FakeHit("draw-dino", 0.95)],
            "topic:auth": [_FakeHit("thought-1", 0.62)],
        },
        texts={
            ("tab-cli-skills", "draw-dino"): "Draw ASCII art dinosaurs.",
            ("topic:auth", "thought-1"): "auth thought",
        },
    )

    rows = recall("query")

    # The skill-routing corpus is excluded — the gate is never even
    # consulted, so its call list stays empty.
    assert gates["tab-cli-skills"].calls == []
    assert all(r["corpus"] != "tab-cli-skills" for r in rows)
    assert any(r["corpus"] == "topic:auth" for r in rows)


def test_recall_skip_corpora_is_overridable() -> None:
    """Passing an empty skip set surfaces every corpus, including routing."""
    recall, _ = _make_tool(
        corpora={
            "tab-cli-skills": [_FakeHit("draw-dino", 0.95)],
        },
        texts={
            ("tab-cli-skills", "draw-dino"): "Draw ASCII art dinosaurs.",
        },
        skip_corpora=frozenset(),
    )

    rows = recall("dinosaur")

    assert [r["corpus"] for r in rows] == ["tab-cli-skills"]


def test_recall_drops_rows_with_missing_text() -> None:
    """A hit whose text_lookup returns None is skipped, not surfaced empty.

    The narrow race the recall module documents: the gate has the row
    in its index but the curator returns ``None`` because the row was
    deleted between the two reads. The model would have nothing to
    quote, so we drop it rather than surface ``text=None``.
    """
    recall, _ = _make_tool(
        corpora={
            "topic:auth": [_FakeHit("ghost", 0.8), _FakeHit("real", 0.7)],
        },
        texts={
            ("topic:auth", "real"): "real thought",
            # ("topic:auth", "ghost") — intentionally absent.
        },
    )

    rows = recall("query")

    assert [r["name"] for r in rows] == ["real"]


# ------------------------------------------------------------- empty input


def test_recall_returns_empty_for_empty_query() -> None:
    recall, gates = _make_tool(
        corpora={"topic:auth": [_FakeHit("thought", 0.9)]},
        texts={("topic:auth", "thought"): "..."},
    )

    assert recall("") == []
    assert recall("   ") == []
    # The gate must not have been called.
    assert gates["topic:auth"].calls == []


def test_recall_returns_empty_when_no_corpora() -> None:
    recall, _ = _make_tool(corpora={}, texts={})
    assert recall("anything") == []


# ----------------------------------------------------- error degradation


def test_recall_collapses_lister_failure_to_error_row() -> None:
    """A grimoire-level failure surfaces as one ``[recall error]`` row.

    The cairn SKILL body treats this shape the same as an empty list
    (tell the user there's nothing to draw on), so the model never
    sees an unhandled tool exception.
    """

    def lister():
        raise RuntimeError("DB unreachable")

    recall = build_recall_tool(
        corpus_lister=lister,
        gate_factory=lambda corpus: _FakeGate([]),
        text_lookup=lambda corpus, name: None,
    )

    rows = recall("query")

    assert len(rows) == 1
    assert rows[0]["corpus"] == "[recall error]"
    assert "DB unreachable" in rows[0]["text"]


def test_recall_continues_when_one_corpus_fails() -> None:
    """One corpus blowing up doesn't kill recall against the others.

    The acceptance signal: a corpus whose gate raises is recorded as
    an error row keyed to that corpus name (so the model knows the
    recall partially succeeded), but other corpora still surface
    their hits.
    """
    good_gate = _FakeGate([_FakeHit("survivor", 0.8)])

    def factory(corpus: str):
        if corpus == "topic:broken":
            raise RuntimeError("schema drift")
        return good_gate

    def lister():
        return ["topic:broken", "topic:fine"]

    def lookup(corpus: str, name: str) -> str | None:
        return "survivor text" if name == "survivor" else None

    recall = build_recall_tool(
        corpus_lister=lister,
        gate_factory=factory,
        text_lookup=lookup,
    )

    rows = recall("query")

    # One real hit + one error row from the broken corpus.
    by_corpus = {row["corpus"]: row for row in rows}
    assert "topic:fine" in by_corpus
    assert by_corpus["topic:fine"]["text"] == "survivor text"
    assert "topic:broken" in by_corpus
    assert "schema drift" in by_corpus["topic:broken"]["text"]


# ------------------------------------------------------- tool query passing


def test_recall_passes_query_through_to_each_gate() -> None:
    recall, gates = _make_tool(
        corpora={
            "topic:a": [_FakeHit("h", 0.8)],
            "topic:b": [_FakeHit("h", 0.7)],
        },
        texts={("topic:a", "h"): "x", ("topic:b", "h"): "y"},
    )

    recall("auth rewrite")

    for corpus, gate in gates.items():
        assert gate.calls, f"gate for {corpus} was not consulted"
        query, _k = gate.calls[0]
        assert query == "auth rewrite"


def test_recall_uses_top_k_per_corpus_in_explain_calls() -> None:
    recall, gates = _make_tool(
        corpora={"topic:a": [_FakeHit("h", 0.8)]},
        texts={("topic:a", "h"): "x"},
        top_k_per_corpus=7,
    )

    recall("query")

    _query, k = gates["topic:a"].calls[0]
    assert k == 7


@pytest.mark.parametrize("missing_seam", ["corpus_lister", "gate_factory", "text_lookup"])
def test_recall_constructs_with_real_default_seams(missing_seam: str) -> None:
    """Default builder construction works without exploding.

    We don't *call* the tool here — that would touch grimoire-core's
    real surface, which the rest of the suite avoids. Constructing
    the builder with each seam's default is the line we care about:
    a typo in the default-factory bindings would surface as a
    ``NameError`` / ``ImportError`` here, before any real DB work.
    """
    kwargs: dict = {
        "corpus_lister": lambda: [],
        "gate_factory": lambda corpus: _FakeGate([]),
        "text_lookup": lambda corpus, name: None,
    }
    kwargs.pop(missing_seam)
    tool = build_recall_tool(**kwargs)
    assert callable(tool)
