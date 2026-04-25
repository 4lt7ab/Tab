"""Typer entry point for the Tab CLI.

Subcommands and agent wiring land in their own tickets. This module
exposes a Typer ``app`` so ``tab --help`` works, plus the ``tab ask``
one-shot subcommand and the ``tab chat`` REPL. ``tab`` invoked without
a subcommand defaults to ``tab chat``.

The five personality dials (humor, directness, warmth, autonomy,
verbosity) are exposed as ``--<dial> INT`` flags on every command.
Layering follows the settings-system synthesis: flag > config file >
tab.md defaults. Conversational mid-session adjustments in ``tab
chat`` apply on top of whatever the flag established for that session.
"""

from __future__ import annotations

import typer

from tab_cli.personality import TabSettings

app = typer.Typer(
    name="tab",
    help="Tab — a verb-shaped CLI agent for the Tab plugin ecosystem.",
    # Bare ``tab`` defaults to ``tab chat`` (per the CLI decision doc),
    # so we don't auto-render help in that case. ``tab --help`` still
    # works because Click handles ``--help`` before dispatch.
    no_args_is_help=False,
    invoke_without_command=True,
    add_completion=False,
)


# Names of the five dials, in display order. Used to keep the flag set,
# the validator, and the resolver in sync — adding a sixth dial means
# editing this tuple plus the per-command Option block.
_DIAL_NAMES = ("humor", "directness", "warmth", "autonomy", "verbosity")


def _validate_dial(name: str, value: int | None) -> None:
    """Range-check one personality flag. Exit non-zero with a readable line on failure.

    The error format ``"<dial> must be 0-100, got <value>"`` is part of
    the CLI's contract — tests pin it. We deliberately don't use
    Typer's ``BadParameter`` wrapper here because that prepends
    ``Usage: ... Error:`` framing, which is hostile in a shell-out
    context (`tab ask --humor 150 ... || handle`). Same instinct as the
    runtime-error path: collapse to one stderr line and exit non-zero.
    """
    if value is None:
        return
    if not 0 <= value <= 100:
        typer.echo(f"{name} must be 0-100, got {value}", err=True)
        raise typer.Exit(code=1)


def _resolve_settings(
    humor: int | None,
    directness: int | None,
    warmth: int | None,
    autonomy: int | None,
    verbosity: int | None,
) -> TabSettings:
    """Layer flags on top of the config file, falling through to tab.md defaults.

    Per the settings-system synthesis (task 01KQ2YXEDHVD2YG1DPD9HEVR2S):
    flag > config file > tab.md defaults. Flags win for the whole
    invocation; anything still unset comes from
    ``~/.config/tab/config.toml``; anything still unset uses
    :class:`TabSettings`'s field defaults (which mirror tab.md's
    Settings table).

    The config file is loaded lazily so a missing or malformed config
    doesn't bring down the bare ``tab --help`` path. Errors inside the
    loader degrade gracefully — it warns to stderr and returns an empty
    dict, which means we just fall through to defaults.
    """
    # Lazy import: keeps `tab --help` cheap and lets tests that don't
    # care about config-file behavior skip stubbing the loader.
    from tab_cli.config import load_settings_from_config

    flag_overrides = {
        "humor": humor,
        "directness": directness,
        "warmth": warmth,
        "autonomy": autonomy,
        "verbosity": verbosity,
    }

    # Start with config-file values (whichever passed validation), then
    # let any explicitly-passed flag win. Unset flags (`None`) don't
    # appear in the merged dict, so `TabSettings`' field defaults fill
    # the rest.
    merged: dict[str, int] = dict(load_settings_from_config())
    for name, value in flag_overrides.items():
        if value is not None:
            merged[name] = value

    return TabSettings(**merged)


def _dial_options() -> dict[str, typer.models.OptionInfo]:
    """Return the five ``--<dial>`` Typer options.

    Defined as a helper so each command's signature stays compact and
    the help text + defaults stay identical across `chat`, `ask`, and
    the root callback. Each option is ``int | None``: ``None`` means
    the user didn't pass the flag, which the resolver reads as "fall
    through to the next layer."
    """
    return {
        name: typer.Option(
            None,
            f"--{name}",
            help=(
                f"Set Tab's {name} dial (0-100) for this invocation. "
                "Overrides the config file and tab.md defaults."
            ),
            show_default=False,
        )
        for name in _DIAL_NAMES
    }


_DIAL_OPTS = _dial_options()


@app.callback()
def _root(
    ctx: typer.Context,
    model: str | None = typer.Option(
        None,
        "--model",
        help=(
            "pydantic-ai model name in <provider:model> form "
            "(e.g. anthropic:claude-sonnet-4). Used by the default "
            "chat REPL when no subcommand is given."
        ),
        show_default=False,
    ),
    humor: int | None = _DIAL_OPTS["humor"],
    directness: int | None = _DIAL_OPTS["directness"],
    warmth: int | None = _DIAL_OPTS["warmth"],
    autonomy: int | None = _DIAL_OPTS["autonomy"],
    verbosity: int | None = _DIAL_OPTS["verbosity"],
) -> None:
    """Root callback. Dispatches bare ``tab`` to the chat REPL.

    ``--model`` and the five ``--<dial>`` options live here too so
    ``tab --humor 90`` works the same as ``tab chat --humor 90`` — the
    bare-``tab``-equals-chat shortcut needs the same flag surface as
    the explicit subcommand.
    """
    if ctx.invoked_subcommand is not None:
        return

    for name, value in (
        ("humor", humor),
        ("directness", directness),
        ("warmth", warmth),
        ("autonomy", autonomy),
        ("verbosity", verbosity),
    ):
        _validate_dial(name, value)

    settings = _resolve_settings(humor, directness, warmth, autonomy, verbosity)

    # Imported lazily so ``tab --help`` and unrelated subcommands don't
    # pay for the agent stack's import cost.
    from tab_cli.chat import run_chat

    try:
        run_chat(model=model, settings=settings)
    except Exception as exc:  # noqa: BLE001 — collapse to readable error
        typer.echo(f"tab: {exc}", err=True)
        raise typer.Exit(code=1) from exc


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
    humor: int | None = _DIAL_OPTS["humor"],
    directness: int | None = _DIAL_OPTS["directness"],
    warmth: int | None = _DIAL_OPTS["warmth"],
    autonomy: int | None = _DIAL_OPTS["autonomy"],
    verbosity: int | None = _DIAL_OPTS["verbosity"],
) -> None:
    """Send a one-shot prompt to Tab and print the response.

    No history, no REPL, no skill routing. One question, one answer.
    Errors (missing API key, network failure, model misconfiguration)
    surface a readable message on stderr and exit non-zero.

    Personality dials (``--humor``, ``--directness``, ``--warmth``,
    ``--autonomy``, ``--verbosity``) accept ints in 0-100. Out-of-range
    values exit non-zero with a one-line ``<dial> must be 0-100, got
    <value>`` message.
    """
    for name, value in (
        ("humor", humor),
        ("directness", directness),
        ("warmth", warmth),
        ("autonomy", autonomy),
        ("verbosity", verbosity),
    ):
        _validate_dial(name, value)

    settings = _resolve_settings(humor, directness, warmth, autonomy, verbosity)

    # Imported lazily so `tab --help` and unrelated subcommands don't pay
    # for pydantic-ai's import cost (and don't fail in environments where
    # the personality file isn't reachable from cwd).
    from tab_cli.personality import compile_tab_agent

    try:
        agent = compile_tab_agent(settings=settings, model=model)
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


@app.command("chat")
def chat(
    model: str | None = typer.Option(
        None,
        "--model",
        help=(
            "pydantic-ai model name in <provider:model> form "
            "(e.g. anthropic:claude-sonnet-4)."
        ),
        show_default=False,
    ),
    humor: int | None = _DIAL_OPTS["humor"],
    directness: int | None = _DIAL_OPTS["directness"],
    warmth: int | None = _DIAL_OPTS["warmth"],
    autonomy: int | None = _DIAL_OPTS["autonomy"],
    verbosity: int | None = _DIAL_OPTS["verbosity"],
) -> None:
    """Start an interactive REPL with the Tab persona.

    Each turn: read input, route through the grimoire skill registry,
    dispatch a matched skill or stream an agent response. ``Ctrl-D``,
    ``/exit``, and ``/quit`` end the session cleanly. Personality
    settings can be adjusted mid-session (e.g. "set humor to 90%") on
    top of whatever ``--humor`` etc. established at startup.

    Errors loading the agent or registry collapse to a readable stderr
    line plus exit code 1, matching ``tab ask``.
    """
    for name, value in (
        ("humor", humor),
        ("directness", directness),
        ("warmth", warmth),
        ("autonomy", autonomy),
        ("verbosity", verbosity),
    ):
        _validate_dial(name, value)

    settings = _resolve_settings(humor, directness, warmth, autonomy, verbosity)

    from tab_cli.chat import run_chat

    try:
        run_chat(model=model, settings=settings)
    except Exception as exc:  # noqa: BLE001
        typer.echo(f"tab: {exc}", err=True)
        raise typer.Exit(code=1) from exc


if __name__ == "__main__":
    app()
