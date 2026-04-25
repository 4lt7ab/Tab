"""Tests for the ``tab think`` Typer subcommand.

The wiring under test mirrors ``test_draw_dino`` and ``test_listen``:
positional words concatenate into a prompt, ``--model`` and the dial
flags round-trip into ``run_skill``, the skill's text reaches stdout,
and any exception collapses to the shared ``tab: <reason>`` /
non-zero-exit contract. We stub ``run_skill`` so the test never
touches a real model — the contract pinned here is the CLI surface,
not the runner internals (``test_skills`` already covers those).

``think`` differs from ``listen`` in one shape detail: it is **not**
sticky. The conversation is the product, but the SKILL body's
question-asking style works fine across normal grimoire-routed turns
inside ``tab chat`` — there is no "Tab silently waits" promise that
forces a sticky branch. Routing-side coverage of think-as-skill-match
inside the REPL is exercised by the generic skill-routing tests in
``test_chat.py`` (which use a stubbed registry that names the matched
skill); this file pins the one-shot Typer surface.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from tab_cli.cli import app


@dataclass
class _RunSkillRecorder:
    """Capture every ``run_skill`` call and return a fixed string."""

    response: str = "What's on your mind?"
    raise_on_call: BaseException | None = None
    calls: list[dict[str, Any]] = field(default_factory=list)

    def __call__(
        self, skill_name: str, user_input: str, **kwargs: Any
    ) -> str:
        self.calls.append(
            {"skill_name": skill_name, "user_input": user_input, **kwargs}
        )
        if self.raise_on_call is not None:
            raise self.raise_on_call
        return self.response


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def isolated_xdg(
    tmp_path: Any, monkeypatch: pytest.MonkeyPatch
) -> Any:
    """Empty ``XDG_CONFIG_HOME`` so config lookups don't read a real file."""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    tab_dir = tmp_path / "tab"
    tab_dir.mkdir()
    return tab_dir


def test_think_invokes_think_skill_with_no_idea(
    runner: CliRunner, isolated_xdg: Any
) -> None:
    """Acceptance criterion #1: ``tab think`` runs the think skill."""
    recorder = _RunSkillRecorder(response="What's on your mind?")

    with patch("tab_cli.skills.run_skill", recorder):
        result = runner.invoke(app, ["think"])

    assert result.exit_code == 0, result.stderr
    assert "What's on your mind" in result.stdout
    assert recorder.calls[0]["skill_name"] == "think"
    # No positional args -> empty user input.
    assert recorder.calls[0]["user_input"] == ""


def test_think_joins_positional_args_into_seed_idea(
    runner: CliRunner, isolated_xdg: Any
) -> None:
    """SKILL.md treats positional words as the optional seed idea."""
    recorder = _RunSkillRecorder()

    with patch("tab_cli.skills.run_skill", recorder):
        result = runner.invoke(
            app,
            ["think", "a", "CLI", "tool", "that", "turns", "markdown",
             "into", "slide", "decks"],
        )

    assert result.exit_code == 0, result.stderr
    assert recorder.calls[0]["user_input"] == (
        "a CLI tool that turns markdown into slide decks"
    )


def test_think_passes_model_flag_to_run_skill(
    runner: CliRunner, isolated_xdg: Any
) -> None:
    recorder = _RunSkillRecorder()

    with patch("tab_cli.skills.run_skill", recorder):
        result = runner.invoke(
            app,
            ["think", "--model", "anthropic:claude-sonnet-4-7", "an idea"],
        )

    assert result.exit_code == 0, result.stderr
    assert recorder.calls[0]["model"] == "anthropic:claude-sonnet-4-7"


def test_think_dial_flags_round_trip_to_run_skill(
    runner: CliRunner, isolated_xdg: Any
) -> None:
    recorder = _RunSkillRecorder()

    with patch("tab_cli.skills.run_skill", recorder):
        result = runner.invoke(
            app,
            [
                "think",
                "--humor", "10",
                "--directness", "20",
                "--warmth", "30",
                "--autonomy", "40",
                "--verbosity", "50",
            ],
        )

    assert result.exit_code == 0, result.stderr
    settings = recorder.calls[0]["settings"]
    assert settings.humor == 10
    assert settings.directness == 20
    assert settings.warmth == 30
    assert settings.autonomy == 40
    assert settings.verbosity == 50


def test_think_out_of_range_dial_exits_non_zero(
    runner: CliRunner, isolated_xdg: Any
) -> None:
    """Same readable-error contract as ``tab ask``."""

    def _boom(*_: Any, **__: Any) -> Any:
        raise AssertionError("run_skill should not run on out-of-range input")

    with patch("tab_cli.skills.run_skill", _boom):
        result = runner.invoke(app, ["think", "--humor", "150"])

    assert result.exit_code != 0
    assert "humor must be 0-100, got 150" in result.stderr


def test_think_surfaces_runtime_errors_as_readable_message(
    runner: CliRunner, isolated_xdg: Any
) -> None:
    """Skill-runner exceptions collapse to ``tab: <reason>`` and exit non-zero."""
    recorder = _RunSkillRecorder(
        raise_on_call=RuntimeError("API key missing")
    )

    with patch("tab_cli.skills.run_skill", recorder):
        result = runner.invoke(app, ["think", "an idea"])

    assert result.exit_code != 0
    assert "tab:" in result.stderr
    assert "API key missing" in result.stderr
    # No half-printed shaping question.
    assert result.stdout.strip() == ""


def test_think_help_lists_the_subcommand_and_flags(
    runner: CliRunner,
) -> None:
    top = runner.invoke(app, ["--help"])
    assert top.exit_code == 0
    assert "think" in top.stdout

    sub = runner.invoke(app, ["think", "--help"])
    assert sub.exit_code == 0
    for dial in ("--humor", "--directness", "--warmth", "--autonomy", "--verbosity"):
        assert dial in sub.stdout, f"{dial} missing from `tab think --help`"
    assert "--model" in sub.stdout


def test_think_unset_flags_fall_through_to_tab_md_defaults(
    runner: CliRunner, isolated_xdg: Any
) -> None:
    """No flags + no config → ``TabSettings`` defaults reach the runner."""
    recorder = _RunSkillRecorder()

    with patch("tab_cli.skills.run_skill", recorder):
        result = runner.invoke(app, ["think"])

    assert result.exit_code == 0, result.stderr
    settings = recorder.calls[0]["settings"]
    assert settings.humor == 65
    assert settings.directness == 80
    assert settings.warmth == 70
    assert settings.autonomy == 50
    assert settings.verbosity == 35


def test_think_unset_flags_fall_through_to_config_file(
    runner: CliRunner, isolated_xdg: Any
) -> None:
    """flag > config file > tab.md defaults — same precedence as other commands."""
    (isolated_xdg / "config.toml").write_text("[settings]\nverbosity = 7\n")

    recorder = _RunSkillRecorder()

    with patch("tab_cli.skills.run_skill", recorder):
        result = runner.invoke(app, ["think"])

    assert result.exit_code == 0, result.stderr
    settings = recorder.calls[0]["settings"]
    assert settings.verbosity == 7     # config-file fallthrough
    assert settings.directness == 80   # tab.md default fallthrough
