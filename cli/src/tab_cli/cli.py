"""Typer entry point for the Tab CLI.

This module wires the verb-shaped command surface — ``tab ask``,
``tab chat``, ``tab <skill>``, ``tab setup``, ``tab grimoire ...`` —
to the implementations that live one import away in their own modules.
The personality-aware verbs (everything that builds a Tab persona
agent) share a single helper in :mod:`tab_cli.commands`: a
``@personality_command`` decorator that exposes the five
``--<dial> INT`` flags + ``--model``, validates dial ranges, resolves
:class:`TabSettings` and the model identifier, and wraps the body in
the readable-error contract before dispatching to a small body that
takes a :class:`TabContext` and the verb's positional arguments.

The five personality dials (humor, directness, warmth, autonomy,
verbosity) are exposed as ``--<dial> INT`` flags on every command.
Layering follows the settings-system synthesis: flag > config file >
tab.md defaults. Conversational mid-session adjustments in ``tab
chat`` apply on top of whatever the flag established for that session.

``tab`` invoked without a subcommand defaults to ``tab chat``.
"""

from __future__ import annotations

import typer

from tab_cli.commands import (
    DIAL_NAMES,
    DIAL_OPTS,
    TabContext,
    error_wrapped,
    join_words,
    model_option,
    personality_command,
    resolve_settings,
    validate_dial,
    validate_dials,
)

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


# Re-exported for callers that reach for the dial-name list at the
# top-level CLI module (none today, but the symbol previously lived
# here). The canonical home is now :mod:`tab_cli.commands`.
_DIAL_NAMES = DIAL_NAMES
_DIAL_OPTS = DIAL_OPTS
_validate_dial = validate_dial
_resolve_settings = resolve_settings


def _resolve_model_or_exit(flag_value: str | None) -> str:
    """Resolve the model string at command-start time, exit-1 on failure.

    Layering matches the dial-resolution pattern: explicit flag wins,
    then config file, then a readable error before any subcommand work
    runs. The early-exit shape matters for ``tab chat`` specifically —
    deferring this check would let the REPL print its prompt, accept
    user input, and then blow up on the first turn with pydantic-ai's
    ``model must either be set on the agent or included when calling
    it`` message. Better to fail at command-start with a hint pointing
    at the fix.

    The error contract — one stderr line plus exit-1 — matches the
    runtime-error path used elsewhere in the CLI (``tab: <reason>``),
    so shell-out callers can do the standard ``|| handle`` idiom.

    Lives in :mod:`tab_cli.cli` (rather than alongside its sibling
    helpers in :mod:`tab_cli.commands`) so the suite-wide test fixture
    ``conftest._stub_model_resolver`` can monkeypatch
    ``tab_cli.cli._resolve_model_or_exit`` and have every subcommand
    pick up the stub. The wrapper in :mod:`tab_cli.commands` looks
    this name up at call time precisely to honor that patch.
    """
    if flag_value is not None and flag_value.strip():
        return flag_value

    # Lazy import: keeps ``tab --help`` cheap and avoids reading the
    # config file when the user passed an explicit ``--model``.
    from tab_cli.config import load_default_model_from_config

    configured = load_default_model_from_config()
    if configured is not None:
        return configured

    typer.echo(
        "tab: no model configured. Pass --model or set [model].default "
        "in ~/.tab/config.toml.\n"
        "Example:\n"
        '  [model]\n'
        '  default = "anthropic:claude-sonnet-4-5"  # or "ollama:gemma4:latest"',
        err=True,
    )
    raise typer.Exit(code=1)


# ----------------------------------------------------------- root callback


@app.callback()
def _root(
    ctx: typer.Context,
    model: str | None = model_option(
        "pydantic-ai model name in <provider:model> form "
        "(e.g. anthropic:claude-sonnet-4). Used by the default "
        "chat REPL when no subcommand is given."
    ),
    humor: int | None = DIAL_OPTS["humor"],
    directness: int | None = DIAL_OPTS["directness"],
    warmth: int | None = DIAL_OPTS["warmth"],
    autonomy: int | None = DIAL_OPTS["autonomy"],
    verbosity: int | None = DIAL_OPTS["verbosity"],
) -> None:
    """Root callback. Dispatches bare ``tab`` to the chat REPL.

    ``--model`` and the five ``--<dial>`` options live here too so
    ``tab --humor 90`` works the same as ``tab chat --humor 90`` — the
    bare-``tab``-equals-chat shortcut needs the same flag surface as
    the explicit subcommand.

    The root callback is the one place we don't route through
    :func:`personality_command`. Typer reserves the callback's
    signature for special semantics (``ctx: typer.Context``,
    ``invoke_without_command``), so we keep the dial+model surface
    declared by hand here and reuse the same validators / resolvers
    the decorator uses. The dispatched body is identical in shape to a
    decorated subcommand body — five-line dispatch into ``run_chat`` —
    so the duplication cost is one Options block.
    """
    if ctx.invoked_subcommand is not None:
        return

    dials = {
        "humor": humor,
        "directness": directness,
        "warmth": warmth,
        "autonomy": autonomy,
        "verbosity": verbosity,
    }
    validate_dials(dials)

    settings = resolve_settings(dials)
    resolved_model = _resolve_model_or_exit(model)

    # Imported lazily so ``tab --help`` and unrelated subcommands don't
    # pay for the agent stack's import cost.
    from tab_cli.chat import run_chat

    try:
        run_chat(model=resolved_model, settings=settings)
    except Exception as exc:  # noqa: BLE001 — collapse to readable error
        typer.echo(f"tab: {exc}", err=True)
        raise typer.Exit(code=1) from exc


# ---------------------------------------------------------- personality verbs


@personality_command(app, "ask")
def ask(
    ctx: TabContext,
    prompt: str = typer.Argument(
        ...,
        help="The prompt to send to Tab as a single-turn question.",
        show_default=False,
    ),
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
    # Imported lazily so `tab --help` and unrelated subcommands don't pay
    # for pydantic-ai's import cost (and don't fail in environments where
    # the personality file isn't reachable from cwd).
    from tab_cli.personality import compile_tab_agent

    agent = compile_tab_agent(settings=ctx.settings, model=ctx.model)
    result = agent.run_sync(prompt)

    # ``result.output`` is the final message text for a string output
    # type — which is the default when no ``output_type`` is configured
    # on the agent (the personality compiler doesn't set one).
    typer.echo(result.output)


@personality_command(app, "draw-dino")
def draw_dino(
    ctx: TabContext,
    request: list[str] = typer.Argument(
        None,
        metavar="[REQUEST]...",
        help=(
            "Optional free-form request (e.g. 'a cute baby pterodactyl'). "
            "Words are joined with single spaces and forwarded to the skill "
            "as the user prompt. Omit for the skill's default 'pick something' "
            "behavior."
        ),
        show_default=False,
    ),
) -> None:
    """Draw an ASCII dinosaur — direct port of the ``draw-dino`` skill.

    Runs ``plugins/tab/skills/draw-dino/SKILL.md`` as the system-prompt
    delta on top of the Tab persona, prints the result to stdout, and
    exits. The same readable-error / non-zero exit contract as
    ``tab ask`` applies — missing model configuration, network failure,
    or a missing SKILL.md collapses to a single ``tab: <reason>`` line
    on stderr.

    The optional ``REQUEST`` words are concatenated with spaces and
    forwarded to the skill as the user prompt. Skipping it is fine; the
    skill's body picks a dino on its own.
    """
    # Lazy import: keeps `tab --help` and unrelated subcommands from
    # paying for pydantic-ai's import cost. Same pattern as `tab ask`.
    from tab_cli.skills import run_skill

    output = run_skill(
        "draw-dino",
        join_words(request),
        settings=ctx.settings,
        model=ctx.model,
    )
    typer.echo(output)


# The ``listen`` / ``think`` / ``teach`` skills exist on the substrate
# and route through ``tab chat`` via grimoire — they don't ship as
# one-shot Typer verbs because their value is multi-turn (silence-then-
# synthesis, sustained back-and-forth, research-then-teach). A one-shot
# port produced only the first turn and trapped users into reading a
# docstring that told them to run ``tab chat`` instead. See
# ``cli/MAINTENANCE.md`` §5.


@personality_command(app, "muse")
def muse(
    ctx: TabContext,
    topic: list[str] = typer.Argument(
        ...,
        metavar="TOPIC...",
        help=(
            "The topic to muse on (e.g. 'auth rewrite'). Words are "
            "joined with single spaces and passed to the muse loop."
        ),
        show_default=False,
    ),
    iterations: int = typer.Option(
        15,
        "--iterations",
        "-n",
        help="Maximum loop iterations before stopping (generation budget).",
    ),
    stale_limit: int = typer.Option(
        3,
        "--stale-limit",
        help="Stop after this many consecutive redundant thoughts.",
    ),
) -> None:
    """Curate a per-topic grimoire by thinking about it out loud.

    Each iteration generates one Tab-voiced sentence about the topic,
    embeds it, and gates against a per-topic grimoire corpus
    (``topic:<slug>``). Novel thoughts get added; redundant ones are
    skipped. Termination is convergence (``--stale-limit`` consecutive
    redundant thoughts) or budget (``--iterations``), whichever fires
    first.

    The corpus persists across calls — re-run ``tab muse <topic>``
    next week and yesterday's thoughts still gate today's. Personality
    dials (``--humor``, ``--directness``, etc.) shape voice the same
    way they do for ``tab chat``.
    """
    from tab_cli.muse import run_muse

    run_muse(
        join_words(topic),
        settings=ctx.settings,
        model=ctx.model,
        budget=iterations,
        stale_limit=stale_limit,
    )


@personality_command(app, "chat")
def chat(ctx: TabContext) -> None:
    """Start an interactive REPL with the Tab persona.

    Each turn: read input, route through the grimoire skill registry,
    dispatch a matched skill or stream an agent response. ``Ctrl-D``,
    ``/exit``, and ``/quit`` end the session cleanly. Personality
    settings can be adjusted mid-session (e.g. "set humor to 90%") on
    top of whatever ``--humor`` etc. established at startup.

    Errors loading the agent or registry collapse to a readable stderr
    line plus exit code 1, matching ``tab ask``.
    """
    from tab_cli.chat import run_chat

    run_chat(model=ctx.model, settings=ctx.settings)


# -------------------------------------------------------------------- setup


@app.command("setup")
@error_wrapped
def setup() -> None:
    """Print the CLI install / provider-key cheat sheet and exit.

    Loads the verbatim block from
    ``cli/src/tab_cli/setup.md`` (shipped inside the wheel) and writes
    it to stdout — no flags, no agent, no network. The same readable-error
    / non-zero exit contract as ``tab ask`` applies if the bundled
    markdown ever goes missing.
    """
    # Lazy import: keeps ``tab --help`` and unrelated subcommands from
    # paying for the (admittedly tiny) ``Path.read_text`` plumbing at
    # import time. Same pattern as the other subcommands in this module.
    from tab_cli.setup import read_setup_body

    body = read_setup_body()

    # ``rstrip("\n")`` so ``typer.echo`` appends exactly one trailing
    # newline regardless of whether ``setup.md`` ends in one. Keeps the
    # smoke-test contract (``tab setup | head -1`` prints ``tab setup``)
    # robust against editor-induced trailing-newline drift.
    typer.echo(body.rstrip("\n"))


# ----------------------------------------------------------------- grimoire
#
# ``tab grimoire`` lives in its own module — three subcommands plus a
# read-only registry helper that doesn't share the dial+model surface
# of the personality verbs. Mounted here so ``tab --help`` advertises
# the group and ``tab grimoire <verb>`` dispatches through the same
# top-level app.

from tab_cli.grimoire_cli import grimoire_app

app.add_typer(grimoire_app, name="grimoire")


if __name__ == "__main__":
    app()
