"""Unit tests for :mod:`tab_cli.registry` — no real DB, no Ollama.

The registry's job is small and well-bounded: read SKILL.md frontmatter,
seed a grimoire corpus, expose ``match(query)``. We test the loader
against the real ``plugins/tab/`` tree (the v0 personality skills are
the fixture) and substitute a deterministic embedder + an in-memory
repository so the gate and curator work without sqlite or Ollama in the
loop.

The fake embedder is a hashed bag-of-words: tokens become 1-bits in a
fixed-dim vector, the repo computes cosine similarity. That gives us a
real semantic-ish signal — overlapping tokens score high, disjoint
tokens score low — without dragging in real embedding machinery.
Mirrors the shape of grimoire-core's own ``tests/test_gate.py`` fakes.

In grimoire-core 0.5.x ``Gate`` is read-only and writes live on
``Curator``, so the loader takes both as paired test seams. Tests build
both off the same in-memory repository, so seeds via the curator are
visible to the gate's ``match``.
"""

from __future__ import annotations

import math
import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import pytest

from grimoire_core import Curator, Gate
from grimoire_core.db.repository import CorpusMeta, ItemSeed, Match
from grimoire_core.embeddings import embedder_from_callable

from tab_cli.registry import (
    DEFAULT_THRESHOLD,
    SKILL_CORPUS,
    SkillFrontmatterError,
    SkillRegistry,
    load_skill_registry,
    parse_skill_frontmatter,
)

# Resolve the worktree's plugins/ directory once. Tests run from the cli/
# package, so up one level to the repo root, then into plugins/.
REPO_ROOT = Path(__file__).resolve().parents[2]
PLUGINS_DIR = REPO_ROOT / "plugins"


# --------------------------------------------------------------- fakes


_STOPWORDS = frozenset(
    {
        "a", "an", "and", "the", "is", "are", "was", "were", "be", "to", "of",
        "in", "on", "at", "for", "with", "by", "from", "as", "or", "but",
        "me", "my", "you", "your", "i", "it", "this", "that", "these", "those",
        "do", "does", "did", "what", "when", "where", "why", "how",
    }
)


def _tokenize(text: str) -> list[str]:
    """Lowercase content tokens with naive stemming.

    Strips a single trailing ``s`` so ``dinosaur``/``dinosaurs`` and
    ``skill``/``skills`` collapse to one bucket — the fake embedder's
    weakest point is the lack of any real morphology, and that single
    rule covers the most common English plural without dragging in a
    real stemmer. Stopwords are dropped so high-frequency glue words
    ("a", "the", "me") don't dominate the cosine signal between a short
    query and a longer description.
    """
    raw = re.findall(r"[a-z0-9]+", text.lower())
    stemmed: list[str] = []
    for token in raw:
        if token in _STOPWORDS:
            continue
        if len(token) > 3 and token.endswith("s") and not token.endswith("ss"):
            token = token[:-1]
        stemmed.append(token)
    return stemmed


_VECTOR_DIM = 256


def _hashed_bag_of_words(text: str) -> list[float]:
    """Hash each token into a fixed-dim vector and L2-normalise.

    Cosine of two such vectors is a weighted Jaccard-like signal: high
    when tokens overlap, near zero when they don't. Good enough for
    "obvious match vs obvious miss" assertions without any real
    embedding machinery — the production embedder is ollama
    nomic-embed-text, which handles morphology and synonymy properly.
    """
    bag = [0.0] * _VECTOR_DIM
    for token in _tokenize(text):
        bag[hash(token) % _VECTOR_DIM] += 1.0
    norm = math.sqrt(sum(v * v for v in bag))
    if norm == 0.0:
        return bag
    return [v / norm for v in bag]


# Stable identity so the corpus_meta path doesn't trip the strictness
# guard. Distinct from any real ollama identity so a stray real Gate
# would not silently accept it.
_FAKE_IDENTITY = "fake:tab-cli-registry-test"


def _make_embedder():
    return embedder_from_callable(_hashed_bag_of_words, identity=_FAKE_IDENTITY)


def _cosine(a: Sequence[float], b: Sequence[float]) -> float:
    return sum(x * y for x, y in zip(a, b, strict=True))


@dataclass
class _Row:
    name: str
    text: str
    vec: list[float]
    threshold: float


class _InMemoryRepository:
    """Just enough of :class:`GrimoireRepository` to drive a Gate + Curator.

    Stores seeded rows in memory, computes cosine on
    ``top_k_in_corpus``, answers ``get_corpus_meta`` from a single
    recorded row. Follows the method-shape grimoire-core's own test
    stubs use; methods the registry never reaches (``apply_corpus``,
    ``rename_item``, etc.) are intentionally absent.

    ``embedded_at`` is a string in grimoire-core 0.5.x's
    :class:`CorpusMeta` (was a ``datetime`` pre-rename); we hand it a
    fixed ISO-8601 stamp so the value is stable across runs.
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


def _make_pair() -> tuple[Gate, Curator]:
    """Build a paired gate + curator over one shared in-memory repo.

    The loader's two test seams (``gate=`` and ``curator=``) need a
    single repository between them — otherwise the curator's seed
    writes into one store and the gate's match reads from another,
    and every match silently misses. The pair-with-shared-repo shape
    is what production looks like too; the only difference is the
    fake repo / fake embedder.
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
    return gate, curator


# ----------------------------------------------------- frontmatter parsing


def test_parse_frontmatter_extracts_required_and_optional_fields(tmp_path: Path) -> None:
    skill = tmp_path / "demo" / "SKILL.md"
    skill.parent.mkdir()
    skill.write_text(
        """---
name: demo
description: "A demo skill that demos things."
argument-hint: "[topic]"
---

# Demo

Body content.
""",
        encoding="utf-8",
    )

    record = parse_skill_frontmatter(skill)

    assert record.name == "demo"
    assert record.description == "A demo skill that demos things."
    assert record.argument_hint == "[topic]"
    assert record.threshold == DEFAULT_THRESHOLD
    assert record.path == skill


def test_parse_frontmatter_rejects_missing_fence(tmp_path: Path) -> None:
    skill = tmp_path / "broken.md"
    skill.write_text("# No frontmatter\n", encoding="utf-8")
    with pytest.raises(SkillFrontmatterError, match="frontmatter fence"):
        parse_skill_frontmatter(skill)


def test_parse_frontmatter_rejects_missing_name(tmp_path: Path) -> None:
    skill = tmp_path / "broken.md"
    skill.write_text(
        """---
description: "no name here"
---

body
""",
        encoding="utf-8",
    )
    with pytest.raises(SkillFrontmatterError, match="'name'"):
        parse_skill_frontmatter(skill)


def test_parse_frontmatter_rejects_missing_description(tmp_path: Path) -> None:
    skill = tmp_path / "broken.md"
    skill.write_text(
        """---
name: lonely
---

body
""",
        encoding="utf-8",
    )
    with pytest.raises(SkillFrontmatterError, match="'description'"):
        parse_skill_frontmatter(skill)


# --------------------------------------------------------- threshold parsing


def _write_skill(
    tmp_path: Path,
    *,
    threshold_line: str | None,
    name: str = "demo",
    description: str = "A demo skill.",
) -> Path:
    """Helper: emit a minimal SKILL.md with an optional threshold line."""
    skill = tmp_path / name / "SKILL.md"
    skill.parent.mkdir(parents=True, exist_ok=True)
    extra = f"{threshold_line}\n" if threshold_line is not None else ""
    skill.write_text(
        f"""---
name: {name}
description: "{description}"
{extra}---

body
""",
        encoding="utf-8",
    )
    return skill


def test_parse_frontmatter_reads_grimoire_threshold(tmp_path: Path) -> None:
    skill = _write_skill(tmp_path, threshold_line="grimoire-threshold: 0.72")
    record = parse_skill_frontmatter(skill)
    assert record.threshold == pytest.approx(0.72)


def test_parse_frontmatter_falls_back_to_default_threshold(tmp_path: Path) -> None:
    skill = _write_skill(tmp_path, threshold_line=None)
    record = parse_skill_frontmatter(skill)
    assert record.threshold == DEFAULT_THRESHOLD


@pytest.mark.parametrize("boundary", [0.0, 1.0])
def test_parse_frontmatter_accepts_threshold_boundaries(
    tmp_path: Path,
    boundary: float,
) -> None:
    skill = _write_skill(
        tmp_path,
        threshold_line=f"grimoire-threshold: {boundary}",
        name=f"boundary-{boundary}".replace(".", "-"),
    )
    record = parse_skill_frontmatter(skill)
    assert record.threshold == pytest.approx(boundary)


def test_parse_frontmatter_rejects_non_numeric_threshold(tmp_path: Path) -> None:
    skill = _write_skill(tmp_path, threshold_line='grimoire-threshold: "high"')
    with pytest.raises(SkillFrontmatterError, match="grimoire-threshold"):
        parse_skill_frontmatter(skill)


def test_parse_frontmatter_rejects_bool_threshold(tmp_path: Path) -> None:
    """A YAML ``true`` is a typo, not a threshold of 1."""
    skill = _write_skill(tmp_path, threshold_line="grimoire-threshold: true")
    with pytest.raises(SkillFrontmatterError, match="grimoire-threshold"):
        parse_skill_frontmatter(skill)


@pytest.mark.parametrize("out_of_range", [-0.01, 1.01, 2.0, -1.0])
def test_parse_frontmatter_rejects_out_of_range_threshold(
    tmp_path: Path,
    out_of_range: float,
) -> None:
    skill = _write_skill(
        tmp_path,
        threshold_line=f"grimoire-threshold: {out_of_range}",
        name=f"oor-{out_of_range}".replace(".", "-").replace("-", "_"),
    )
    with pytest.raises(SkillFrontmatterError, match=r"\[0, 1\]"):
        parse_skill_frontmatter(skill)


def test_parse_frontmatter_threshold_error_includes_path(tmp_path: Path) -> None:
    """Validation errors are keyed to the offending SKILL.md path."""
    skill = _write_skill(tmp_path, threshold_line="grimoire-threshold: 1.5")
    with pytest.raises(SkillFrontmatterError) as excinfo:
        parse_skill_frontmatter(skill)
    assert str(skill) in str(excinfo.value)


def test_load_skill_registry_threads_per_skill_threshold_to_gate(
    tmp_path: Path,
) -> None:
    """End-to-end: a custom grimoire-threshold on one skill flows to Curator.seed.

    The acceptance signal: build a synthetic plugins tree with two
    skills, give one of them a non-default threshold, load through
    `load_skill_registry`, and confirm the seeded row carries the
    override (and the other row carries the fallback).
    """
    skills_dir = tmp_path / "tab" / "skills"
    skills_dir.mkdir(parents=True)

    (skills_dir / "tuned").mkdir()
    (skills_dir / "tuned" / "SKILL.md").write_text(
        """---
name: tuned
description: "Tuned skill with a custom bar."
grimoire-threshold: 0.81
---

body
""",
        encoding="utf-8",
    )

    (skills_dir / "default").mkdir()
    (skills_dir / "default" / "SKILL.md").write_text(
        """---
name: default
description: "Default skill, no override."
---

body
""",
        encoding="utf-8",
    )

    gate, curator = _make_pair()
    registry = load_skill_registry(tmp_path, gate=gate, curator=curator)

    by_name = {record.name: record for record in registry.records}
    assert by_name["tuned"].threshold == pytest.approx(0.81)
    assert by_name["default"].threshold == DEFAULT_THRESHOLD

    # And the curator wrote those same per-row thresholds into the
    # corpus — pull a top-1 via the gate for each skill's own
    # description so the threshold field on the returned Hit is the
    # seeded threshold for that row.
    tuned_hit = registry.match("Tuned skill with a custom bar.")
    assert tuned_hit is not None
    assert tuned_hit.name == "tuned"
    assert tuned_hit.threshold == pytest.approx(0.81)

    default_hit = registry.match("Default skill, no override.")
    assert default_hit is not None
    assert default_hit.name == "default"
    assert default_hit.threshold == pytest.approx(DEFAULT_THRESHOLD)


# --------------------------------------------------------------- loader


def test_load_skill_registry_walks_personality_plugin() -> None:
    """All four v0 personality skills appear in the loaded registry."""
    gate, curator = _make_pair()
    registry = load_skill_registry(PLUGINS_DIR, gate=gate, curator=curator)

    names = {record.name for record in registry.records}

    # The four v0 skills the task acceptance criteria call out.
    assert {"draw-dino", "listen", "think", "teach"} <= names

    # hey-tab is in the tree today (being reworked into `tab setup`
    # separately). The loader still picks it up — that's the documented
    # behaviour in the task summary.
    assert "hey-tab" in names


def test_load_skill_registry_assigns_default_threshold_to_every_record() -> None:
    gate, curator = _make_pair()
    registry = load_skill_registry(PLUGINS_DIR, gate=gate, curator=curator)

    assert registry.records  # not empty
    for record in registry.records:
        assert record.threshold == DEFAULT_THRESHOLD


def test_match_routes_obvious_query_to_draw_dino_above_threshold() -> None:
    """Acceptance signal: an obvious draw-dino query clears draw-dino's bar.

    The fake embedder is a hashed bag-of-words — a literal-token proxy
    for what nomic-embed-text would do semantically. The query is
    phrased to share enough content tokens with the draw-dino
    description ("Draw ASCII art dinosaurs ...") that cosine clears
    the default threshold; the routing-to-draw-dino half of the
    assertion is the load-bearing one. With a real semantic embedder
    at runtime, looser phrasings ("draw me a dinosaur") would also
    clear; the fake here is a deliberately strict proxy that fails
    closed rather than open.
    """
    gate, curator = _make_pair()
    registry = load_skill_registry(PLUGINS_DIR, gate=gate, curator=curator)

    hit = registry.match("draw an ASCII art dinosaur")

    assert hit is not None, "expected a hit for an obvious draw-dino query"
    assert hit.name == "draw-dino", (
        f"expected top-1 to be draw-dino, got {hit.name} "
        f"(similarity={hit.similarity:.3f}); is the fake embedder ranking "
        f"another skill higher because of accidental token overlap?"
    )
    # ``passed`` is informational here — grimoire-core 0.5.x's
    # ``Gate.match`` filters non-passing hits server-side, so a
    # non-None hit has already cleared its bar. We still assert the
    # flag so a future relaxation of the adapter catches our eye.
    assert hit.passed, (
        f"expected draw-dino to clear its threshold, "
        f"got similarity={hit.similarity:.3f} threshold={hit.threshold:.3f}"
    )


def test_match_returns_silent_for_obviously_unrelated_input() -> None:
    """Acceptance signal: unrelated input does not pass any skill's bar.

    "What is the capital of Mongolia" shares no meaningful tokens with
    any of the v0 skill descriptions, so cosine is near-zero across the
    board and nothing clears the default threshold. In grimoire-core
    0.5.x ``Gate.match`` filters below-threshold rows out, so silence
    surfaces as a flat ``None`` from the registry adapter — no
    ``passed=False`` middle ground anymore.
    """
    gate, curator = _make_pair()
    registry = load_skill_registry(PLUGINS_DIR, gate=gate, curator=curator)

    hit = registry.match("what is the capital of Mongolia")
    assert hit is None, (
        f"expected silence, got passing hit name={hit.name} "
        f"similarity={hit.similarity:.3f}"
    )


# ----------------------------------------------------------- registry shape


def test_skill_registry_records_are_immutable() -> None:
    gate, curator = _make_pair()
    registry = load_skill_registry(PLUGINS_DIR, gate=gate, curator=curator)
    assert isinstance(registry.records, tuple)


def test_skill_registry_exposes_underlying_gate() -> None:
    gate, curator = _make_pair()
    registry = load_skill_registry(PLUGINS_DIR, gate=gate, curator=curator)
    assert isinstance(registry, SkillRegistry)
    assert registry.gate is gate


def test_load_skill_registry_raises_when_skills_directory_missing(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_skill_registry(tmp_path)


def test_load_skill_registry_handles_empty_skills_directory(tmp_path: Path) -> None:
    """An empty skills directory yields a registry with no records.

    Whether that's intentional (a fresh checkout before plugins land)
    or a packaging miss is the caller's call — see the loader docstring.
    No curator is needed: the loader skips curator construction
    entirely when ``records`` is empty, so the test seam stays clean
    without a settings-backed default sneaking in.
    """
    (tmp_path / "tab" / "skills").mkdir(parents=True)
    gate, _curator = _make_pair()
    registry = load_skill_registry(tmp_path, gate=gate)
    assert registry.records == ()
    # Gate works; just nothing seeded.
    assert registry.match("anything") is None


# ----------------------------------------------------- multi-source loader


def test_load_skill_registry_merges_extra_skill_dirs(tmp_path: Path) -> None:
    """``extra_skill_dirs`` records seed alongside the plugin records.

    The CLI-only home (``cli/src/tab_cli/skills/``) plumbs through this
    parameter in production. The acceptance signal: a skill in the
    extra dir shows up in ``registry.records`` and matches via the
    same gate as the plugin-tree skills.
    """
    plugin_skills = tmp_path / "tab" / "skills"
    plugin_skills.mkdir(parents=True)
    (plugin_skills / "shared").mkdir()
    (plugin_skills / "shared" / "SKILL.md").write_text(
        """---
name: shared
description: "A skill that lives in the plugin tree."
---

body
""",
        encoding="utf-8",
    )

    cli_skills = tmp_path / "cli_local"
    cli_skills.mkdir()
    (cli_skills / "cliside").mkdir()
    (cli_skills / "cliside" / "SKILL.md").write_text(
        """---
name: cliside
description: "A CLI-only skill that lives next to the runtime."
---

body
""",
        encoding="utf-8",
    )

    gate, curator = _make_pair()
    registry = load_skill_registry(
        tmp_path,
        gate=gate,
        curator=curator,
        extra_skill_dirs=[cli_skills],
    )

    names = {r.name for r in registry.records}
    assert names == {"shared", "cliside"}

    # The CLI-only record matches via the same gate.
    cli_hit = registry.match("A CLI-only skill that lives next to the runtime.")
    assert cli_hit is not None
    assert cli_hit.name == "cliside"


def test_load_skill_registry_silently_skips_missing_extra_dirs(
    tmp_path: Path,
) -> None:
    """A missing CLI-local dir is benign — empty checkouts mustn't crash.

    Production passes ``cli_skills_dir()`` even when no CLI-only
    skills exist. The loader treats ``is_dir()`` false as "no extra
    records to seed" rather than raising — same shape as the empty-
    skills-dir case.
    """
    plugin_skills = tmp_path / "tab" / "skills"
    plugin_skills.mkdir(parents=True)
    (plugin_skills / "alone").mkdir()
    (plugin_skills / "alone" / "SKILL.md").write_text(
        """---
name: alone
description: "Only skill in the tree."
---

body
""",
        encoding="utf-8",
    )

    gate, curator = _make_pair()
    registry = load_skill_registry(
        tmp_path,
        gate=gate,
        curator=curator,
        extra_skill_dirs=[tmp_path / "does-not-exist"],
    )

    assert {r.name for r in registry.records} == {"alone"}


def test_load_skill_registry_rejects_duplicate_names_across_sources(
    tmp_path: Path,
) -> None:
    """A name collision between the plugin tree and a CLI-only dir loads loudly.

    Silently letting one source shadow another would make the
    override implicit. The registry's contract is silence-by-default
    on misses but loud-by-default on misconfiguration; this is the
    misconfiguration shape.
    """
    plugin_skills = tmp_path / "tab" / "skills"
    plugin_skills.mkdir(parents=True)
    (plugin_skills / "twin").mkdir()
    (plugin_skills / "twin" / "SKILL.md").write_text(
        """---
name: twin
description: "The plugin-tree copy."
---

body
""",
        encoding="utf-8",
    )

    cli_skills = tmp_path / "cli_local"
    cli_skills.mkdir()
    (cli_skills / "twin").mkdir()
    (cli_skills / "twin" / "SKILL.md").write_text(
        """---
name: twin
description: "The CLI-local copy."
---

body
""",
        encoding="utf-8",
    )

    gate, curator = _make_pair()
    with pytest.raises(SkillFrontmatterError, match="duplicate"):
        load_skill_registry(
            tmp_path,
            gate=gate,
            curator=curator,
            extra_skill_dirs=[cli_skills],
        )
