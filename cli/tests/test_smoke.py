"""Smoke test: the Typer app loads and `--help` prints a help screen with `tab`."""

from __future__ import annotations

from typer.testing import CliRunner

from tab_cli.cli import app


def test_help_mentions_tab() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "tab" in result.stdout.lower()
