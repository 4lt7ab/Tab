"""Tests for :mod:`tab_cli.skills` — the personality-skill runner.

The runner is the shared machinery behind the four personality-skill
ports (``draw-dino``, ``listen``, ``teach``, ``think``). Each port is a
thin wrapper; almost every interesting behaviour lives here:

- ``read_skill_body`` opens the actual ``plugins/tab/skills/<name>/SKILL.md``
  and returns its body sans frontmatter. The acceptance criterion for
  the draw-dino port pins exactly this — behaviour is driven by the
  markdown file, not by a Python-side copy of the prompt.
- ``build_skill_system_prompt`` composes Tab's persona prompt with the
  skill body so personality dials remain live during a skill turn.
- ``run_skill`` runs one synchronous turn against a model. We stub the
  agent so the test never touches a provider; the assertion is that the
  user input round-trips through ``run_sync`` and the result reaches
  the caller.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

from tab_cli.personality import TabSettings
from tab_cli.skills import (
    SkillNotFoundError,
    build_skill_system_prompt,
    compile_skill_agent,
    read_skill_body,
    run_skill,
)

# Two parents up: ``cli/tests/test_skills.py`` → ``cli/`` → ``<repo>``.
REPO_ROOT = Path(__file__).resolve().parents[2]
PLUGINS_DIR = REPO_ROOT / "plugins"


# ---------------------------------------------------------------- read_skill_body


def test_read_skill_body_returns_markdown_body_without_frontmatter() -> None:
    """Acceptance criterion #4: the loader reads the actual SKILL.md.

    The body that comes back must contain content unique to the
    draw-dino skill and must NOT contain the YAML frontmatter delimiters
    or fields. Anchoring on a phrase pulled from the file (rather than
    reading the file twice in the test) keeps the assertion specific
    while staying tolerant of unrelated body edits.
    """
    body = read_skill_body("draw-dino", plugins_dir=PLUGINS_DIR)

    # File-specific content from the body — these phrases are part of
    # the skill's voice, not boilerplate, so a refactor that swaps the
    # right file in won't accidentally still pass.
    assert "ASCII art dinosaurs" in body
    assert "Reference Templates" in body
    assert "Always deliver" in body

    # Frontmatter must not bleed through.
    assert not body.startswith("---")
    assert "argument-hint" not in body
    # The frontmatter sets `description: "..."`. The body's prose should
    # not include that bare key-value form.
    assert 'name: draw-dino' not in body


def test_read_skill_body_raises_for_unknown_skill(tmp_path: Path) -> None:
    """Missing SKILL.md must surface a typed error, not a bare OSError.

    The chat dispatch and Typer subcommand both surface this through
    the ``tab: <reason>`` collapse — a typed exception lets the wrapper
    distinguish "this skill isn't registered" from a transient I/O
    issue if we ever want to.
    """
    # Build a real-shaped tree but with no skill folder in it.
    (tmp_path / "tab" / "skills").mkdir(parents=True)
    with pytest.raises(SkillNotFoundError, match="draw-dino"):
        read_skill_body("draw-dino", plugins_dir=tmp_path)


def test_read_skill_body_resolves_cli_local_skill() -> None:
    """The no-arg form finds skills under ``cli/src/tab_cli/skills/``.

    ``cairn`` is the first CLI-only skill — its SKILL.md lives next
    to the runtime, not in the plugin tree, because its capability
    depends on grimoire-core which the Claude Code plugin host can't
    provide. The resolver must fall through plugin-tree to CLI-local
    so the chat dispatch can compile the agent without callers
    plumbing a separate path.
    """
    body = read_skill_body("cairn")

    # File-specific body content — these phrases anchor the cairn
    # SKILL.md's voice and survive unrelated edits.
    assert "Cairn" in body
    assert "recall" in body.lower()

    # Frontmatter must not bleed through.
    assert not body.startswith("---")
    assert "name: cairn" not in body


def test_read_skill_body_test_seam_does_not_fall_through_to_cli_local(
    tmp_path: Path,
) -> None:
    """``plugins_dir=`` is a test seam — it must not consult the CLI-local home.

    The seam exists so tests can build a synthetic plugins tree and
    get deterministic resolution. If a missing skill in the synthetic
    tree silently fell through to the real ``cli_skills_dir()``, a
    test that meant to assert "this skill is missing" would
    accidentally find ``cairn`` (or any other on-disk CLI-local
    skill) and the failure mode would be invisible.
    """
    (tmp_path / "tab" / "skills").mkdir(parents=True)
    # ``cairn`` exists on disk under cli_skills_dir(), but the test
    # seam should refuse to look there.
    with pytest.raises(SkillNotFoundError, match="cairn"):
        read_skill_body("cairn", plugins_dir=tmp_path)


def test_read_skill_body_strips_frontmatter_for_a_synthetic_skill(
    tmp_path: Path,
) -> None:
    """Frontmatter stripping mirrors the personality compiler's rule.

    Pinning this against a synthetic file keeps the test independent of
    the real plugin's contents — if someone swaps the SKILL.md format,
    this case fails specifically on the format change rather than
    masquerading as a content drift.
    """
    skill_dir = tmp_path / "tab" / "skills" / "fake"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        """---
name: fake
description: "for the test"
---

# Fake

Body line one.
Body line two.
""",
        encoding="utf-8",
    )

    body = read_skill_body("fake", plugins_dir=tmp_path)
    assert body.startswith("# Fake")
    assert "Body line one." in body
    assert "Body line two." in body
    assert "description:" not in body


# ---------------------------------------------------------- build_skill_system_prompt


def test_build_skill_system_prompt_includes_persona_and_skill_body() -> None:
    """The skill prompt is persona + skill body — both halves must appear."""
    prompt = build_skill_system_prompt("draw-dino", plugins_dir=PLUGINS_DIR)

    # Persona half: the settings preamble's opening phrase pins this.
    assert "Your active personality settings" in prompt

    # Skill half: a phrase from draw-dino's body.
    assert "ASCII art dinosaurs" in prompt

    # Order: persona first, skill body second. A skill-body delta is
    # supposed to *extend* the persona, not be obscured by it.
    persona_idx = prompt.index("Your active personality settings")
    skill_idx = prompt.index("ASCII art dinosaurs")
    assert persona_idx < skill_idx


def test_build_skill_system_prompt_reflects_overridden_settings() -> None:
    """Custom :class:`TabSettings` must reach the skill prompt's preamble."""
    settings = TabSettings(humor=12, verbosity=88)
    prompt = build_skill_system_prompt(
        "draw-dino", settings=settings, plugins_dir=PLUGINS_DIR
    )

    assert "Humor 12%" in prompt
    assert "Verbosity 88%" in prompt


# ---------------------------------------------------------------- run_skill


@dataclass
class _StubResult:
    """Minimal stand-in for ``pydantic_ai.AgentRunResult``."""

    output: str


@dataclass
class _StubAgent:
    """Records every ``run_sync`` call so the round-trip can be asserted."""

    response: str = "drawn"
    runs: list[tuple[tuple[Any, ...], dict[str, Any]]] = field(default_factory=list)

    def run_sync(self, *args: Any, **kwargs: Any) -> _StubResult:
        self.runs.append((args, kwargs))
        return _StubResult(output=self.response)


def test_run_skill_round_trips_user_input_and_returns_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """User input must reach ``run_sync`` and the agent's output must come back."""
    agent = _StubAgent(response="here is your dino")
    captured: list[dict[str, Any]] = []

    def _fake_compile(skill_name: str, **kwargs: Any) -> _StubAgent:
        captured.append({"skill_name": skill_name, **kwargs})
        return agent

    monkeypatch.setattr("tab_cli.skills.compile_skill_agent", _fake_compile)

    out = run_skill("draw-dino", "a baby pterodactyl")

    assert out == "here is your dino"
    assert len(captured) == 1
    assert captured[0]["skill_name"] == "draw-dino"
    assert agent.runs == [(("a baby pterodactyl",), {})]


def test_run_skill_passes_settings_and_model_through(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``settings`` and ``model`` round-trip into the compile call."""
    agent = _StubAgent()
    captured: list[dict[str, Any]] = []

    def _fake_compile(skill_name: str, **kwargs: Any) -> _StubAgent:
        captured.append({"skill_name": skill_name, **kwargs})
        return agent

    monkeypatch.setattr("tab_cli.skills.compile_skill_agent", _fake_compile)

    settings = TabSettings(humor=5)
    run_skill(
        "draw-dino",
        "",
        settings=settings,
        model="anthropic:claude-sonnet-4-7",
    )

    assert captured[0]["settings"] is settings
    assert captured[0]["model"] == "anthropic:claude-sonnet-4-7"


def test_run_skill_propagates_skill_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    """A missing skill bubbles up as :class:`SkillNotFoundError`."""

    def _boom(skill_name: str, **_: Any) -> Any:
        raise SkillNotFoundError(f"no SKILL.md for {skill_name!r}")

    monkeypatch.setattr("tab_cli.skills.compile_skill_agent", _boom)

    with pytest.raises(SkillNotFoundError, match="draw-dino"):
        run_skill("draw-dino", "anything")


# -------------------------------------------------------- compile_skill_agent


def test_compile_skill_agent_builds_an_agent_with_combined_prompt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The compiled agent's system prompt must be the combined persona + skill body.

    We don't run the agent — we capture the kwargs the constructor saw.
    """
    captured: list[dict[str, Any]] = []

    class _StubPydanticAgent:
        def __init__(self, **kwargs: Any) -> None:
            captured.append(kwargs)

    monkeypatch.setattr("pydantic_ai.Agent", _StubPydanticAgent)

    agent = compile_skill_agent("draw-dino", plugins_dir=PLUGINS_DIR)

    assert isinstance(agent, _StubPydanticAgent)
    assert len(captured) == 1
    prompt = captured[0]["system_prompt"]
    # Same shape as ``build_skill_system_prompt`` — persona + body.
    assert "Your active personality settings" in prompt
    assert "ASCII art dinosaurs" in prompt
    # Default model deferral matches ``compile_tab_agent``.
    assert captured[0]["defer_model_check"] is True
