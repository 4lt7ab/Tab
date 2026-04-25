"""Typer entry point for the Tab CLI.

Subcommands and agent wiring land in their own tickets. This module
exposes a Typer ``app`` so ``tab --help`` works, plus the ``tab ask``
one-shot subcommand: compile the Tab agent, run a single turn, print
the response, exit.
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


@app.command("ask")
def ask(
    prompt: str = typer.Argument(
        ...,
        help="The prompt to send to Tab as a single-turn question.",
        show_default=False,
    ),
    model: str | None = typer.Option(
        None,
        "--model",
        help=(
            "pydantic-ai model name in <provider:model> form "
            "(e.g. anthropic:claude-sonnet-4)."
        ),
        show_default=False,
    ),
) -> None:
    """Send a one-shot prompt to Tab and print the response.

    No history, no REPL, no skill routing. One question, one answer.
    Errors (missing API key, network failure, model misconfiguration)
    surface a readable message on stderr and exit non-zero.
    """
    # Imported lazily so `tab --help` and unrelated subcommands don't pay
    # for pydantic-ai's import cost (and don't fail in environments where
    # the personality file isn't reachable from cwd).
    from tab_cli.personality import compile_tab_agent

    try:
        agent = compile_tab_agent(model=model)
        result = agent.run_sync(prompt)
    except Exception as exc:  # noqa: BLE001 — surface anything as a readable error
        # Typer's default behavior on uncaught exceptions is a traceback
        # dump, which is hostile in a shell-out / CI context. We collapse
        # to a one-line stderr message and a non-zero exit so callers can
        # do the usual `|| handle` shell idiom.
        typer.echo(f"tab: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    # `result.output` is the final message text for a string output type
    # — which is the default when no `output_type` is configured on the
    # agent (the personality compiler doesn't set one).
    typer.echo(result.output)


if __name__ == "__main__":
    app()
