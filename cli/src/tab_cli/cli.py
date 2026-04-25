"""Typer entry point for the Tab CLI.

Subcommands and agent wiring land in their own tickets. This module just
exposes a Typer `app` so `tab --help` works.
"""

from __future__ import annotations

import typer

app = typer.Typer(
    name="tab",
    help="Tab — a verb-shaped CLI agent for the Tab plugin ecosystem.",
    no_args_is_help=True,
    add_completion=False,
)


@app.callback()
def _root() -> None:
    """Root callback — present so `tab` with no args shows help."""


if __name__ == "__main__":
    app()
