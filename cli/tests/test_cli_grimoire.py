"""End-to-end tests for the ``tab grimoire`` Typer subcommand surface.

Exercises ``set``, ``reset``, ``show`` against a fake
``XDG_CONFIG_HOME`` so the persisted store is fully sandboxed. ``show``
is the most important assertion — it pins the source-of-value contract
(``override`` / ``frontmatter`` / ``loader-default``) per the design
synthesis.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from tab_cli.cli import app


@pytest.fixture
def fake_xdg(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Sandbox the override store at ``$XDG_CONFIG_HOME/tab/``."""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    return tmp_path / "tab"


# --------------------------------------------------------- discoverability


def test_grimoire_command_is_registered() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "grimoire" in result.stdout


def test_grimoire_help_lists_all_three_subcommands() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["grimoire", "--help"])
    assert result.exit_code == 0
    for sub in ("set", "reset", "show"):
        assert sub in result.stdout


# ---------------------------------------------------------------- set


def test_set_writes_override_to_disk(fake_xdg: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["grimoire", "set", "draw-dino", "0.45"])
    assert result.exit_code == 0, result.stdout

    raw = (fake_xdg / "grimoire-overrides.json").read_text(encoding="utf-8")
    decoded = json.loads(raw)
    assert decoded["thresholds"] == {"draw-dino": 0.45}


def test_set_out_of_range_exits_nonzero_with_readable_error(fake_xdg: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["grimoire", "set", "draw-dino", "1.5"])
    assert result.exit_code == 1
    # The CLI's stderr contract: ``tab: <reason>`` on one line.
    assert result.stderr.startswith("tab:")
    assert "0.0, 1.0" in result.stderr or "[0.0, 1.0]" in result.stderr


def test_set_negative_exits_nonzero(fake_xdg: Path) -> None:
    runner = CliRunner()
    # ``--`` ends Typer/Click's flag parsing so a leading-dash
    # argument is treated as a positional value, not an unknown option.
    result = runner.invoke(app, ["grimoire", "set", "--", "draw-dino", "-0.1"])
    assert result.exit_code == 1
    assert result.stderr.startswith("tab:")


# --------------------------------------------------------------- reset


def test_reset_clears_an_existing_override(fake_xdg: Path) -> None:
    runner = CliRunner()
    runner.invoke(app, ["grimoire", "set", "draw-dino", "0.45"])
    result = runner.invoke(app, ["grimoire", "reset", "draw-dino"])
    assert result.exit_code == 0, result.stdout
    assert "reset" in result.stdout

    decoded = json.loads(
        (fake_xdg / "grimoire-overrides.json").read_text(encoding="utf-8")
    )
    assert decoded["thresholds"] == {}


def test_reset_is_idempotent_when_nothing_set(fake_xdg: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["grimoire", "reset", "draw-dino"])
    # Idempotent: not a hard error, just a one-line note.
    assert result.exit_code == 0, result.stdout
    assert "no override" in result.stdout


# ---------------------------------------------------------------- show


def test_show_prints_every_loaded_skill_with_loader_default(fake_xdg: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["grimoire", "show"])
    assert result.exit_code == 0, result.stdout

    # Each row is ``<name>\t<threshold>\t<source>``. The four v0
    # personality skills must appear; with no overrides set, every
    # source reads as ``loader-default``.
    lines = result.stdout.strip().splitlines()
    rows = {line.split("\t")[0]: line.split("\t") for line in lines}

    expected_skills = {"draw-dino", "listen", "teach", "think"}
    assert expected_skills <= set(rows.keys())

    for name in expected_skills:
        cells = rows[name]
        assert len(cells) == 3, f"expected 3 columns for {name}, got {cells}"
        assert cells[2] == "loader-default", (
            f"expected source 'loader-default' for {name}, got {cells[2]!r}"
        )


def test_show_marks_overridden_skill_with_override_source(fake_xdg: Path) -> None:
    runner = CliRunner()
    runner.invoke(app, ["grimoire", "set", "draw-dino", "0.45"])
    result = runner.invoke(app, ["grimoire", "show"])
    assert result.exit_code == 0, result.stdout

    # Find the draw-dino row and assert source + threshold.
    found = False
    for line in result.stdout.splitlines():
        cells = line.split("\t")
        if cells and cells[0] == "draw-dino":
            assert cells[2] == "override", line
            assert cells[1] == "0.45", line
            found = True
            break
    assert found, f"draw-dino row missing from show output:\n{result.stdout}"


def test_set_then_show_round_trips(fake_xdg: Path) -> None:
    """Acceptance criterion: 'Set-then-show round-trips through the store'."""
    runner = CliRunner()
    set_result = runner.invoke(app, ["grimoire", "set", "teach", "0.7"])
    assert set_result.exit_code == 0, set_result.stdout

    show_result = runner.invoke(app, ["grimoire", "show"])
    assert show_result.exit_code == 0, show_result.stdout

    teach_row = next(
        (line for line in show_result.stdout.splitlines() if line.startswith("teach\t")),
        None,
    )
    assert teach_row is not None, show_result.stdout
    cells = teach_row.split("\t")
    assert cells[1] == "0.7"
    assert cells[2] == "override"


def test_show_after_reset_reverts_source(fake_xdg: Path) -> None:
    """Reset clears the override; show no longer reports it."""
    runner = CliRunner()
    runner.invoke(app, ["grimoire", "set", "listen", "0.6"])
    runner.invoke(app, ["grimoire", "reset", "listen"])
    result = runner.invoke(app, ["grimoire", "show"])
    assert result.exit_code == 0, result.stdout

    listen_row = next(
        (line for line in result.stdout.splitlines() if line.startswith("listen\t")),
        None,
    )
    assert listen_row is not None, result.stdout
    cells = listen_row.split("\t")
    assert cells[2] == "loader-default", cells


def test_show_surfaces_malformed_overrides_file(fake_xdg: Path) -> None:
    """A malformed overrides file should surface as a readable error.

    The user almost certainly typoed something — silently dropping
    the bad row would mean the CLI keeps quoting old values. Better
    to refuse and tell the user.
    """
    fake_xdg.mkdir()
    (fake_xdg / "grimoire-overrides.json").write_text("not json", encoding="utf-8")
    runner = CliRunner()
    result = runner.invoke(app, ["grimoire", "show"])
    assert result.exit_code == 1
    assert result.stderr.startswith("tab:")
    assert "malformed" in result.stderr
