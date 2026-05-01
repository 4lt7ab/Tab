"""Grimoire registry loader for the personality plugin's SKILL.md files.

The CLI's job at startup is to figure out which skill (if any) the user
just invoked. Rather than rebuild a gating layer, we lean on grimoire:
each ``SKILL.md`` becomes a gated row in a corpus, with the skill's
``description`` as the match-text. ``match(query)`` then asks grimoire
"does this clear any item's bar?" — silent below threshold, named hit
above.

The loader is deliberately small. It walks
``plugins/tab/skills/*/SKILL.md``, parses YAML frontmatter for ``name``
and ``description`` (``argument-hint`` is optional), and seeds a
:class:`grimoire_core.Gate` with the resulting rows. The chat/ask wiring
holds the registry and queries it per turn — silence-by-default is the
safety property; below-threshold input falls through to the agent.

What the loader does **not** do:

- Invoke skills. It returns "this input matches skill X above
  threshold" or "no match"; what to do next is the caller's business.

Per-skill thresholds are read from each SKILL.md's optional
``grimoire-threshold`` frontmatter key (a float in ``[0, 1]``); a skill
that omits the key inherits :data:`DEFAULT_THRESHOLD`.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from tab_cli.paths import FrontmatterError, parse_frontmatter

if TYPE_CHECKING:  # avoid forcing grimoire's backend import path at module load
    from grimoire_core import Curator, Gate, Hit


# The corpus key under which all v0 personality-skill rows live. Single
# corpus is the right shape today — every skill is a peer, threshold is
# uniform, and grimoire's mismatch-detection works at the corpus level.
SKILL_CORPUS = "tab-cli-skills"


# Fallback threshold for a SKILL.md that omits ``grimoire-threshold``.
# Calibrated against ollama's ``nomic-embed-text`` on description-shaped
# prompts: cosine similarity for an obvious paraphrase ("draw me a
# dinosaur" against the draw-dino description) sits comfortably above
# this; an unrelated query ("what's the weather in Berlin") sits below.
#
# Picking too-low here over-routes (false positives, the agent never
# sees a chunk of input); picking too-high under-routes (skills silently
# miss). Mid-range biases toward under-routing, which is the safer
# failure mode given silence-by-default. Per-skill overrides via
# ``grimoire-threshold:`` in SKILL.md frontmatter are the per-item
# tuning surface.
DEFAULT_THRESHOLD = 0.55


@dataclass(frozen=True, slots=True)
class SkillRecord:
    """One parsed ``SKILL.md`` ready to seed grimoire.

    ``threshold`` carries the per-row gate bar straight to
    :meth:`grimoire_core.Curator.seed`. A SKILL.md may set
    ``grimoire-threshold`` in its frontmatter to override; absent the
    override, the loader fills in :data:`DEFAULT_THRESHOLD`.
    """

    name: str
    description: str
    threshold: float
    path: Path
    argument_hint: str | None = None


class SkillFrontmatterError(FrontmatterError):
    """A ``SKILL.md`` was missing required frontmatter or malformed.

    Loud rather than skipped: the CLI's whole gating story rests on
    correct registration, and a silently-dropped skill would make the
    agent feel mysteriously unresponsive. Better to fail loading and
    surface the broken file.

    Subclasses :class:`tab_cli.paths.FrontmatterError` so the shared
    :func:`tab_cli.paths.parse_frontmatter` errors are still catchable
    as ``SkillFrontmatterError`` from this module's call sites — the
    registry's own validation (missing ``name`` / ``description``,
    bad ``grimoire-threshold``) keeps raising this name directly.
    """


class SkillRegistry:
    """Holds the loaded skill records and wraps the grimoire gate.

    The registry is what ``tab chat`` and ``tab ask`` consult per turn:
    given user input, did anything match? The wrapper is intentionally
    thin — it exposes :meth:`match` (gating) and :attr:`records` (what
    was registered, for diagnostics and the ``tab list`` surface that
    will follow). Any deeper grimoire call (``explain``, ``neighbors``)
    can reach :attr:`gate` directly.
    """

    def __init__(self, gate: Gate, records: Iterable[SkillRecord]) -> None:
        self._gate = gate
        # Tuple, not list: the registry is read-mostly post-load and
        # downstream callers shouldn't be able to mutate the snapshot
        # they got back.
        self._records: tuple[SkillRecord, ...] = tuple(records)

    @property
    def gate(self) -> Gate:
        """The underlying :class:`grimoire_core.Gate`. Exposed for diagnostics."""
        return self._gate

    @property
    def records(self) -> tuple[SkillRecord, ...]:
        """Every skill registered in load order."""
        return self._records

    def match(self, query: str) -> Hit | None:
        """Return the top-1 :class:`grimoire_core.Hit` for ``query``, or ``None``.

        Adapter over :meth:`grimoire_core.Gate.match`, which returns a
        list of passed hits (silence-by-default — non-passing rows are
        filtered out, not surfaced with ``passed=False``). We unwrap to
        ``Hit | None`` for the chat wiring's ergonomics. For diagnostic
        "almost matched X at 0.51 vs 0.55" output, reach
        :attr:`gate` and call :meth:`grimoire_core.Gate.explain` directly.
        """
        hits = self._gate.match(query)
        return hits[0] if hits else None


def parse_skill_frontmatter(path: Path) -> SkillRecord:
    """Read a ``SKILL.md`` and return its parsed frontmatter.

    Required keys: ``name``, ``description``. Optional: ``argument-hint``,
    ``grimoire-threshold``. Anything else in the frontmatter is ignored —
    the parent ``CLAUDE.md`` documents the convention for Claude Code
    runtime fields, and ``grimoire-threshold`` is the CLI's runtime field
    for tuning the per-skill match bar.

    ``grimoire-threshold`` must be a number in ``[0, 1]`` when present;
    missing falls back to :data:`DEFAULT_THRESHOLD`. Bools are rejected
    even though Python treats them as ``int`` — a YAML ``true`` is almost
    certainly a typo, not a threshold of 1.

    Raises :class:`SkillFrontmatterError` for missing/invalid documents.
    """
    text = path.read_text(encoding="utf-8")
    frontmatter = _extract_frontmatter(text, path)

    name = frontmatter.get("name")
    description = frontmatter.get("description")

    if not isinstance(name, str) or not name.strip():
        raise SkillFrontmatterError(
            f"{path}: missing or empty 'name' in frontmatter",
        )
    if not isinstance(description, str) or not description.strip():
        raise SkillFrontmatterError(
            f"{path}: missing or empty 'description' in frontmatter",
        )

    argument_hint_raw = frontmatter.get("argument-hint")
    if argument_hint_raw is not None and not isinstance(argument_hint_raw, str):
        raise SkillFrontmatterError(
            f"{path}: 'argument-hint' must be a string when present",
        )

    threshold = _parse_threshold(frontmatter.get("grimoire-threshold"), path)

    return SkillRecord(
        name=name.strip(),
        description=description.strip(),
        threshold=threshold,
        path=path,
        argument_hint=argument_hint_raw.strip() if argument_hint_raw else None,
    )


def load_skill_registry(
    plugins_dir: Path,
    *,
    gate: Gate | None = None,
    curator: Curator | None = None,
    extra_skill_dirs: Iterable[Path] = (),
) -> SkillRegistry:
    """Walk ``plugins_dir/tab/skills/*/SKILL.md`` and seed a grimoire gate.

    The signature documented in the task is ``(plugins_dir) ->
    SkillRegistry``; the keyword-only ``gate=`` / ``curator=`` are
    test seams. ``gate`` is the read side (used by :meth:`SkillRegistry.match`),
    ``curator`` is the write side (used here to seed the SKILL.md rows
    into the corpus). When either is omitted, the function constructs
    the canonical pair via :meth:`grimoire_core.Gate.from_settings`
    and :meth:`grimoire_core.Curator.from_settings` (Ollama + the
    shared backing store). Tests typically inject a paired fake
    (gate + curator sharing one in-memory repository) so the seeded
    rows are visible to the gate's match call.

    The split mirrors grimoire-core's own API shape (v0.5.x and later):
    ``Gate`` is read-only, authoring lives on ``Curator``. One seam
    per role.

    ``extra_skill_dirs`` accepts additional directories whose immediate
    children each hold a ``SKILL.md``. Production wires
    :func:`tab_cli.paths.cli_skills_dir` here so the CLI-local skill
    home (``cli/src/tab_cli/skills/<name>/SKILL.md``) seeds into the
    same gate as the plugin substrate. Each path is treated like the
    plugin ``skills/`` dir — its layout is ``<dir>/<name>/SKILL.md``,
    not ``<dir>/tab/skills/<name>/SKILL.md``. Missing directories are
    silently skipped (a fresh checkout where the CLI dir has no skills
    yet shouldn't crash); a dir that exists but has zero ``SKILL.md``
    files is also fine.

    Returns a :class:`SkillRegistry` ready to answer ``match(query)``.

    Notes:

    - The walker descends into ``plugins_dir/tab/skills/`` and each
      ``extra_skill_dirs`` entry. Records are merged into one corpus
      (:data:`SKILL_CORPUS`) so a single ``match`` answers across all
      sources.
    - Duplicate skill names across sources raise :class:`SkillFrontmatterError`
      — silently letting one source shadow another would make the
      override implicit, and the registry's whole job is to be
      explicit about what fired.
    - Skills are seeded in sorted order so the registry is
      deterministic across runs (filesystem iteration order isn't).
    - An empty skills directory is not an error; the registry returns
      no matches. Whether that's the user's intent or a packaging miss
      is the caller's call. We also skip building a default curator
      in that case — the corpus stays untouched.
    """
    plugin_skills_dir = plugins_dir / "tab" / "skills"
    if not plugin_skills_dir.is_dir():
        raise FileNotFoundError(
            f"expected personality skills directory at {plugin_skills_dir}",
        )

    # Sort by skill-folder name within each source. The glob pattern
    # keeps us scoped to immediate children of each skills dir —
    # nested ``SKILL.md`` files would be a structural surprise and
    # shouldn't be silently picked up.
    skill_md_paths: list[Path] = sorted(plugin_skills_dir.glob("*/SKILL.md"))
    for extra in extra_skill_dirs:
        if not extra.is_dir():
            # Missing extra-source dir is benign: a fresh checkout may
            # not have CLI-local skills yet, and the production caller
            # always passes ``cli_skills_dir()`` even when empty.
            continue
        skill_md_paths.extend(sorted(extra.glob("*/SKILL.md")))

    records = [parse_skill_frontmatter(path) for path in skill_md_paths]

    # Duplicate-name check spans every source. Two SKILL.md files
    # claiming the same ``name`` would seed two rows under one corpus
    # key on :meth:`Curator.seed`'s upsert semantics — last write wins
    # silently — and the user-visible match would flicker between them
    # depending on filesystem order. Better to fail at load.
    seen: dict[str, Path] = {}
    for record in records:
        prior = seen.get(record.name)
        if prior is not None:
            raise SkillFrontmatterError(
                f"duplicate skill name {record.name!r} in {record.path} "
                f"(also at {prior})",
            )
        seen[record.name] = record.path

    if gate is None or (records and curator is None):
        # Lazy import: grimoire_core's ``from_settings`` constructors
        # pull in the embedder and DB connection at first call. Tests
        # that inject both seams avoid the import entirely, which
        # keeps the ``tab_cli.registry`` module cheap to import in
        # environments that don't have the runtime stack wired up yet.
        # ``ensure_migrated`` is idempotent and cached, so the second
        # call site (in muse.py) hits a no-op.
        from tab_cli.grimoire_runtime import ensure_migrated

        ensure_migrated()

        from grimoire_core import Curator as _Curator
        from grimoire_core import Gate as _Gate

        if gate is None:
            gate = _Gate.from_settings(corpus=SKILL_CORPUS)
        if records and curator is None:
            curator = _Curator.from_settings(corpus=SKILL_CORPUS)

    if records and curator is not None:
        curator.seed(
            (record.name, record.description, record.threshold)
            for record in records
        )

    return SkillRegistry(gate=gate, records=records)


# --------------------------------------------------------------- internals


def _extract_frontmatter(text: str, path: Path) -> dict[str, object]:
    """Pull the YAML frontmatter block out of a Markdown file.

    Thin wrapper around :func:`tab_cli.paths.parse_frontmatter` that
    re-raises the shared :class:`tab_cli.paths.FrontmatterError` as the
    registry's :class:`SkillFrontmatterError` so callers (and tests) that
    catch the registry-shaped name keep working — same messages, same
    triggers (no fence, unclosed fence, non-mapping body).
    """
    try:
        frontmatter, _body = parse_frontmatter(text, path)
    except FrontmatterError as exc:
        raise SkillFrontmatterError(str(exc)) from exc
    return frontmatter


def _parse_threshold(value: object, path: Path) -> float:
    """Validate an optional ``grimoire-threshold`` frontmatter value.

    ``None`` (key absent) falls back to :data:`DEFAULT_THRESHOLD`.
    A real number in ``[0, 1]`` passes through. Anything else raises
    :class:`SkillFrontmatterError` with the path keyed in the message —
    bool is treated as not-a-number even though Python's ``isinstance``
    would accept it as ``int``, because a YAML ``true`` here is almost
    always a typo.
    """
    if value is None:
        return DEFAULT_THRESHOLD
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise SkillFrontmatterError(
            f"{path}: 'grimoire-threshold' must be a number in [0, 1], "
            f"got {type(value).__name__}",
        )
    threshold = float(value)
    if not 0.0 <= threshold <= 1.0:
        raise SkillFrontmatterError(
            f"{path}: 'grimoire-threshold' must be in [0, 1], got {threshold}",
        )
    return threshold
