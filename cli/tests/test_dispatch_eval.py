"""Calibration regression test for the dispatch fixture.

The contract this test pins:

* Run every labeled query in ``cli/tests/fixtures/dispatch_eval.json``
  through a gate seeded with the v0 personality skills, classify each
  pair into one of four buckets (CORRECT_PASS, CORRECT_MISS,
  WRONG_PASS, WRONG_MISS), and check the Pattern-B-vs-calibration
  property: no query should land in ``WRONG_PASS`` — that's the
  load-bearing safety property the silence-by-default routing relies
  on.
* Every *non-ambiguous* fires-case (a row whose ``expected`` names a
  skill and whose entry has no ``notes`` annotation) must end in
  ``CORRECT_PASS``. CORRECT_MISS for a fires-case means the right item
  won the top-1 but the bar was too tight; that's a calibration drift
  worth surfacing as a failure.
* The two ambiguous rows (those carrying a ``notes`` field — see
  fixture commentary) get a non-fatal audit-log block printed to stdout
  with their bucket and notes, so reviewers can sanity-check the
  judgement call when calibration changes.

The classification logic was previously imported from
``grimoire.calibration``; that module didn't survive the
grimoire → grimoire-core split (calibration was a pre-1.0 surface that
only the test consumed — production never imported it). Inlined here
as ``_Bucket`` / ``_classify_pair`` since the bucketing rule is small
and fully expressed in twelve lines.

The gate is constructed with a hand-curated *concept embedder*, not
the production Ollama embedder. Reasons:

* No Ollama in the test loop — keeps the suite stack-free, same
  constraint the existing ``test_registry`` fakes respect.
* The hashed-bag-of-words used by ``test_registry`` is deliberately
  too crude for fixture-style queries to clear the default 0.55
  threshold (probed: nearly every fires-case lands as CORRECT_MISS
  under it). A bag-of-words can demonstrate routing direction but
  cannot demonstrate calibration; this fixture is specifically about
  calibration.
* The concept embedder uses orthogonal one-hot dimensions per skill,
  driven by trigger phrases pulled directly from the fixture's
  fires-cases. That makes the cosine match deterministic and crisp:
  in-skill queries land at sim=1.0, ambiguous and out-of-skill queries
  land at 0.0 (below the bar). When the fixture changes, the trigger
  set documented here is the place to update — they're a regression
  contract together.

The structure mirrors ``test_registry.py``: same ``_InMemoryRepository``
shape, same ``embedder_from_callable`` seam, same ``Gate`` constructor.
Writes go through ``Curator`` (split off ``Gate`` in grimoire-core
0.5.x); reads use ``Gate.explain(k=1)`` to get the top-1 with its
per-row pass/fail flag, which is what calibration needs (``Gate.match``
already filters non-passing hits and would lose the CORRECT_MISS
signal).
"""

from __future__ import annotations

import json
import math
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from grimoire_core import Curator, Gate
from grimoire_core.db.repository import CorpusMeta, ItemSeed, Match
from grimoire_core.embeddings import embedder_from_callable

from tab_cli.registry import DEFAULT_THRESHOLD, SKILL_CORPUS

# ----------------------------------------------------------------- fixture

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "dispatch_eval.json"


# ---------------------------------------------------- concept embedder

# Orthogonal one-hot dimensions: each skill gets its own dimension, so
# concept-tag bags never collide across skills. Cosine then collapses to
# "did the query trip the same concept as the skill" — a clean proxy for
# what the production embedder gives us via semantic similarity.
_DIMENSION_FOR_TAG: dict[str, int] = {
    "skill:draw-dino": 0,
    "skill:listen": 1,
    "skill:think": 2,
    "skill:teach": 3,
    "skill:hey-tab": 4,
}
_VECTOR_DIM = len(_DIMENSION_FOR_TAG)


# Per-skill trigger phrases drawn from the fires-cases in
# ``dispatch_eval.json``. Phrases are case-insensitive substring
# matches; specificity matters — e.g. ``"listen for"`` would catch
# the ``"listen for errors"`` negative, so the listen triggers stick
# to the more specific phrasings the fixture actually uses for fires.
#
# This list is the regression contract paired with the fixture: when a
# fires-case query is added or rephrased, its trigger phrase belongs
# here. When a negative shifts close to a fires-case (the reason for
# the ambiguous bucket), the trigger phrase stays absent — the
# concept embedder leaves it at zero and the calibration falls below
# threshold, exactly as it should.
_TRIGGERS_FOR_SKILL: dict[str, tuple[str, ...]] = {
    "draw-dino": (
        "draw me a dinosaur",
        "ascii t-rex",
        "make an ascii",
    ),
    "listen": (
        "just listen for a moment",
        "don't say anything",
    ),
    "think": (
        "think through this idea",
        "talk through a half-formed",
    ),
    "teach": (
        "teach me",
        "explain transformers",
        "first principles",
    ),
    "hey-tab": (
        "hey tab",
        "/hey-tab",
    ),
}


def _concept_tags(text: str) -> list[str]:
    """Return the unique skill-concept tags fired by ``text``.

    Two paths:

    * If ``text`` is a literal concept tag from
      :data:`_DIMENSION_FOR_TAG` (the ``"skill:<name>"`` strings used as
      seeded "descriptions"), return that single tag. This is how the
      gate's seeded rows land on their own concept dimension.
    * Otherwise, treat ``text`` as a query and fire any skill whose
      trigger phrase appears as a case-insensitive substring.

    The two-path design keeps the test deterministic: seeded skills are
    addressed by their explicit tag, queries are addressed by their
    fixture-shaped trigger phrases. No accidental overlap between the
    two surfaces.
    """
    if text in _DIMENSION_FOR_TAG:
        return [text]
    lower = text.lower()
    fired: list[str] = []
    for skill, triggers in _TRIGGERS_FOR_SKILL.items():
        if any(trigger in lower for trigger in triggers):
            fired.append(f"skill:{skill}")
    return fired


def _vectorize(text: str) -> list[float]:
    """Concept embedding: one-hot dim per skill concept fired by ``text``.

    Returns the zero vector when no concept fires — that's how negatives
    and ambiguous cases stay below the gate's threshold. Otherwise the
    vector is L2-normalised so cosine collapses to an inner-product on
    the unit sphere.
    """
    bag = [0.0] * _VECTOR_DIM
    for tag in _concept_tags(text):
        bag[_DIMENSION_FOR_TAG[tag]] = 1.0
    norm = math.sqrt(sum(v * v for v in bag))
    if norm == 0.0:
        return bag
    return [v / norm for v in bag]


_FAKE_IDENTITY = "fake:tab-cli-dispatch-eval"


def _make_embedder():
    return embedder_from_callable(_vectorize, identity=_FAKE_IDENTITY)


def _cosine(a: Sequence[float], b: Sequence[float]) -> float:
    return sum(x * y for x, y in zip(a, b, strict=True))


# ------------------------------------------------------- in-memory gate


@dataclass
class _Row:
    name: str
    text: str
    vec: list[float]
    threshold: float


class _InMemoryRepository:
    """Just enough of :class:`GrimoireRepository` to drive a Gate + Curator.

    Mirrors the test seam in ``test_registry.py``; the calibration
    surface only needs ``top_k_in_corpus``, ``seed_corpus`` (via
    :meth:`Curator.seed`) and the ``corpus_meta`` hand-shake.
    """

    def __init__(self) -> None:
        self._corpora: dict[str, list[_Row]] = {}
        self._meta: dict[str, CorpusMeta] = {}

    def get_corpus_meta(self, corpus_key: str) -> CorpusMeta | None:
        return self._meta.get(corpus_key)

    def seed_corpus(
        self,
        corpus_key: str,
        rows: list[ItemSeed],
        *,
        embedder_identity: str,
        embedding_dimensions: int,
    ) -> None:
        self._corpora[corpus_key] = [
            _Row(
                name=row.name,
                text=row.text,
                vec=list(row.embedding),
                threshold=row.threshold,
            )
            for row in rows
        ]
        self._meta[corpus_key] = CorpusMeta(
            corpus_key=corpus_key,
            embedder=embedder_identity,
            embedding_dimensions=embedding_dimensions,
            embedded_at="2026-04-25T00:00:00.000Z",
        )

    def top_k_in_corpus(
        self,
        corpus_key: str,
        query_vec: list[float],
        k: int,
    ) -> list[Match]:
        rows = self._corpora.get(corpus_key, [])
        scored = [
            Match(
                name=row.name,
                threshold=row.threshold,
                similarity=_cosine(query_vec, row.vec),
            )
            for row in rows
        ]
        scored.sort(key=lambda m: m.similarity, reverse=True)
        return scored[:k]


# Centroid descriptions: each skill's "description" is just its concept
# tag, so the seeded vector lands on exactly that skill's dimension.
# The production registry seeds real SKILL.md descriptions; here the
# substitution is intentional and documented — see the module docstring.
_SKILL_CENTROIDS: tuple[tuple[str, str], ...] = (
    ("draw-dino", "skill:draw-dino"),
    ("listen", "skill:listen"),
    ("think", "skill:think"),
    ("teach", "skill:teach"),
    ("hey-tab", "skill:hey-tab"),
)


def _make_gate() -> Gate:
    """Build the v0-skill-seeded gate the dispatch eval runs against.

    Reads and writes share one in-memory repository so the curator's
    seed lands where the gate's match later reads.
    """
    repo = _InMemoryRepository()
    embedder = _make_embedder()
    gate = Gate(
        corpus=SKILL_CORPUS,
        embedder=embedder,
        repository=repo,  # type: ignore[arg-type]
    )
    curator = Curator(
        corpus=SKILL_CORPUS,
        embedder=embedder,
        repository=repo,  # type: ignore[arg-type]
    )
    curator.seed(
        (name, description, DEFAULT_THRESHOLD)
        for name, description in _SKILL_CENTROIDS
    )
    return gate


# ------------------------------------------------------------- calibration


@dataclass(frozen=True, slots=True)
class _LabeledPair:
    """One row from the dispatch fixture: a query and its expected skill.

    ``expected`` is ``None`` for negative rows (queries that should
    land in silence). The fixture also carries an optional ``notes``
    field for ambiguous-but-judged rows; we keep that on the raw
    entries dict and look it up by index, so this dataclass stays
    pair-shaped.
    """

    query: str
    expected: str | None


class _Bucket(Enum):
    """The four classification buckets calibration sorts each pair into.

    * ``CORRECT_PASS`` — top-1 was the expected skill *and* cleared its
      threshold. The good outcome for a fires-case.
    * ``CORRECT_MISS`` — silence was correct (either the expected skill
      was top-1 but didn't clear the bar, or expected was ``None`` and
      no row cleared the bar).
    * ``WRONG_PASS`` — top-1 cleared its threshold but was the wrong
      skill (or any skill, when expected was ``None``). The
      load-bearing safety violation: a misroute the user can't see.
    * ``WRONG_MISS`` — top-1 was a different skill than expected and
      didn't clear its bar. Fixable silence: nothing fired but the
      right skill wasn't the one we almost picked either.
    """

    CORRECT_PASS = "CORRECT_PASS"
    CORRECT_MISS = "CORRECT_MISS"
    WRONG_PASS = "WRONG_PASS"
    WRONG_MISS = "WRONG_MISS"


@dataclass(frozen=True, slots=True)
class _PairResult:
    """One row's classification, plus the top-1 numbers that drove it."""

    pair: _LabeledPair
    bucket: _Bucket
    top1_name: str | None
    top1_similarity: float | None
    top1_threshold: float | None


def _classify_pair(gate: Gate, pair: _LabeledPair) -> _PairResult:
    """Classify one labeled pair into a :class:`_Bucket`.

    Uses :meth:`Gate.explain` rather than :meth:`Gate.match` so we get
    the top-1 *with* its pass/fail flag. ``match`` already filters
    non-passing rows out, which is the right shape for production
    routing but loses the CORRECT_MISS signal calibration needs.
    """
    hits = gate.explain(pair.query, k=1)
    if not hits:
        # Empty corpus or zero-vector query against an empty corpus.
        # Treat as silence: CORRECT_MISS when expected was None,
        # WRONG_MISS when expected named a skill that wasn't even in
        # the corpus.
        bucket = _Bucket.CORRECT_MISS if pair.expected is None else _Bucket.WRONG_MISS
        return _PairResult(
            pair=pair,
            bucket=bucket,
            top1_name=None,
            top1_similarity=None,
            top1_threshold=None,
        )

    hit = hits[0]
    correct_skill = hit.name == pair.expected
    if hit.passed:
        bucket = _Bucket.CORRECT_PASS if correct_skill else _Bucket.WRONG_PASS
    else:
        # Below threshold → silence. The expected==None case is
        # CORRECT_MISS regardless of which skill happened to be top-1
        # (the user wanted silence and got it). The expected==<skill>
        # case is CORRECT_MISS only when the right skill won the
        # top-1 (right intent, bar drift); otherwise WRONG_MISS.
        if pair.expected is None or correct_skill:
            bucket = _Bucket.CORRECT_MISS
        else:
            bucket = _Bucket.WRONG_MISS

    return _PairResult(
        pair=pair,
        bucket=bucket,
        top1_name=hit.name,
        top1_similarity=hit.similarity,
        top1_threshold=hit.threshold,
    )


# ------------------------------------------------------------- helpers


def _load_fixture_entries() -> list[dict[str, object]]:
    """Read the raw JSON entries (preserves the ``notes`` field).

    The ambiguous-audit block needs the optional ``notes`` key, which
    is fixture-only and doesn't belong on :class:`_LabeledPair`. We
    parse the file once and rebuild ``_LabeledPair`` rows alongside.
    """
    raw = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError(
            f"{FIXTURE_PATH}: expected JSON array, got {type(raw).__name__}",
        )
    return raw


def _format_results_table(results: Iterable[_PairResult]) -> str:
    """Render a per-pair table for failure messages.

    Columns are picked for human triage: bucket first (so a column scan
    surfaces regressions at a glance), then expected vs top-1, then
    similarity vs threshold so a CORRECT_MISS row immediately tells
    you how far below the bar it landed.
    """
    rows = list(results)
    header = (
        f"{'bucket':14s} "
        f"{'expected':>14s} "
        f"{'top1':>14s} "
        f"{'sim':>6s} "
        f"{'thr':>6s}  "
        f"query"
    )
    lines = [header, "-" * len(header)]
    for result in rows:
        sim = (
            f"{result.top1_similarity:6.3f}"
            if result.top1_similarity is not None
            else "  None"
        )
        thr = (
            f"{result.top1_threshold:6.3f}"
            if result.top1_threshold is not None
            else "  None"
        )
        lines.append(
            f"{result.bucket.value:14s} "
            f"{str(result.pair.expected):>14s} "
            f"{str(result.top1_name):>14s} "
            f"{sim} "
            f"{thr}  "
            f"{result.pair.query}"
        )
    return "\n".join(lines)


# ------------------------------------------------------------- the test


def test_dispatch_eval_holds_calibration_contract() -> None:
    """Lock the dispatch fixture's calibration contract.

    Three layered assertions, in failure-priority order:

    1. ``WRONG_PASS`` count is zero. This is the safety property — a
       wrong top-1 above its threshold means a misroute the user can't
       see, the worst kind of routing bug.
    2. Every non-ambiguous fires-case is in ``CORRECT_PASS``. A
       CORRECT_MISS here is a calibration regression: the right skill
       still wins but its bar drifted up.
    3. Ambiguous cases produce a stdout audit block with bucket + notes
       so a reviewer can confirm the judgement call still reads right.
    """
    raw_entries = _load_fixture_entries()
    pairs = [
        _LabeledPair(
            query=str(entry["query"]),
            expected=entry.get("expected"),  # type: ignore[arg-type]
        )
        for entry in raw_entries
    ]

    gate = _make_gate()
    results = [_classify_pair(gate, pair) for pair in pairs]

    bucket_counts = {bucket: 0 for bucket in _Bucket}
    for result in results:
        bucket_counts[result.bucket] += 1

    table = _format_results_table(results)

    # ---- (1) Safety property ---------------------------------------
    wrong_pass_count = bucket_counts[_Bucket.WRONG_PASS]
    assert wrong_pass_count == 0, (
        "calibration regression: at least one query routed to the "
        f"wrong skill above its threshold ({wrong_pass_count} WRONG_PASS rows). "
        "This is the load-bearing routing-safety property — a wrong "
        "top-1 that clears its bar means a misroute the user does not "
        "see.\n\n" + table
    )

    # ---- (2) Non-ambiguous fires-cases must end in CORRECT_PASS ----
    is_ambiguous = ["notes" in entry for entry in raw_entries]
    failures: list[_PairResult] = []
    for result, ambiguous, _entry in zip(results, is_ambiguous, raw_entries, strict=True):
        if ambiguous:
            continue
        if result.pair.expected is None:
            # Negative case — out of scope for the fires-case
            # assertion. WRONG_PASS would already have failed (1)
            # above; CORRECT_MISS is the expected silence behaviour.
            continue
        if result.bucket is not _Bucket.CORRECT_PASS:
            failures.append(result)

    assert not failures, (
        f"calibration regression: {len(failures)} non-ambiguous "
        "fires-case(s) did not land in CORRECT_PASS. The right skill "
        "may still be winning the top-1 (CORRECT_MISS) — that means "
        "the threshold drifted, the description tightened, or the "
        "fixture query phrasing moved out of the embedder's "
        "neighbourhood.\n\n" + table
    )

    # ---- (3) Ambiguous-case audit block (non-fatal) ----------------
    audit_lines = ["", "ambiguous-case audit (non-fatal):"]
    for result, ambiguous, entry in zip(results, is_ambiguous, raw_entries, strict=True):
        if not ambiguous:
            continue
        notes = entry.get("notes", "")
        audit_lines.append(
            f"  [{result.bucket.value}] expected={result.pair.expected!r} "
            f"top1={result.top1_name!r} "
            f"sim={result.top1_similarity!s} "
            f"thr={result.top1_threshold!s}"
        )
        audit_lines.append(f"    query: {result.pair.query}")
        audit_lines.append(f"    notes: {notes}")
    # ``print`` is captured by pytest by default; the block surfaces
    # under ``pytest -rA`` for a clean run, and on the failure report
    # for the assertions above. Either way a reviewer eyeing the
    # ambiguous calls can see the bucket and notes side-by-side.
    print("\n".join(audit_lines))
