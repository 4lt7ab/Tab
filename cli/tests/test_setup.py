"""Tests for ``tab setup`` — the install / provider-key cheat sheet command.

The acceptance criteria for the subcommand are explicit:

- runs without arguments and prints the synthesized block to stdout
- the block content is loaded from a markdown file checked into the CLI
  package, not hardcoded
- ``tab setup | head -1`` prints ``tab setup``

Each assertion below pins one of those, plus a couple of structural
checks that catch likely regressions (stripped trailing whitespace,
missing pydantic-ai key list, etc.) without re-stating the entire file.
"""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from tab_cli.cli import app
from tab_cli.setup import read_setup_body

# Two parents up: ``cli/tests/test_setup.py`` → ``cli/`` → ``cli`` (root).
SETUP_MD = (
    Path(__file__).resolve().parents[1] / "src" / "tab_cli" / "setup.md"
)


def test_setup_md_is_a_real_file_in_the_package() -> None:
    """The substrate principle: the body is a checked-in markdown file."""
    assert SETUP_MD.is_file(), f"expected setup body at {SETUP_MD}"
    # Sanity: the file has the expected leading line. Pinning the first
    # line keeps the test a real "loads from disk" check rather than
    # accidentally passing on whatever in-memory string the runner
    # produces.
    first_line = SETUP_MD.read_text(encoding="utf-8").splitlines()[0]
    assert first_line == "tab setup"


def test_read_setup_body_returns_file_contents_verbatim() -> None:
    """``read_setup_body`` reads the on-disk file, byte-for-byte."""
    body = read_setup_body()
    expected = SETUP_MD.read_text(encoding="utf-8")
    assert body == expected


def test_setup_command_prints_block_to_stdout() -> None:
    """The Typer subcommand emits the file's body to stdout and exits 0."""
    runner = CliRunner()
    result = runner.invoke(app, ["setup"])

    assert result.exit_code == 0, result.stdout

    # Acceptance criterion: the first line of the printed output is
    # exactly ``tab setup`` — the header that the user will see when
    # they pipe through ``head -1``.
    first_line = result.stdout.splitlines()[0]
    assert first_line == "tab setup"

    # Spot-check a phrase from each numbered section so a future
    # accidental truncation of ``setup.md`` (or a regex-replace gone
    # wrong) trips a specific assertion. Anchoring on the unique tokens
    # rather than full lines keeps the test stable across whitespace
    # tweaks.
    assert "uv tool install tab" in result.stdout
    assert "ANTHROPIC_API_KEY" in result.stdout
    assert "GEMINI_API_KEY" in result.stdout
    assert "GROQ_API_KEY" in result.stdout
    assert "OLLAMA_HOST" in result.stdout
    assert "claude mcp add --scope user --transport stdio tab tab mcp" in result.stdout
    assert "/hey-tab" in result.stdout
    assert "https://github.com/4lt7ab/Tab" in result.stdout


def test_setup_command_takes_no_arguments() -> None:
    """Running ``tab setup`` bare succeeds (acceptance: 'runs without arguments')."""
    runner = CliRunner()
    # No args, no flags — must succeed.
    result = runner.invoke(app, ["setup"])
    assert result.exit_code == 0


def test_setup_help_lists_command() -> None:
    """``tab --help`` should advertise the ``setup`` subcommand.

    Keeps the discoverability contract: a user who runs ``tab --help``
    sees ``setup`` in the command list. If a future refactor accidentally
    drops the ``@app.command`` decorator, this test fires before the
    smoke test does.
    """
    runner = CliRunner()
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "setup" in result.stdout
