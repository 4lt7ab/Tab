"""Shared scaffolding for ``tab`` subcommands.

This module exists to kill an 8-site duplication in
:mod:`tab_cli.cli`. Every personality-aware subcommand (``tab``'s root
callback, ``ask``, ``mcp``, ``draw-dino``, ``listen``, ``think``,
``teach``, ``chat``) used to repeat the same shape:

1. Five ``--<dial> INT`` Options (humor, directness, warmth, autonomy,
   verbosity).
2. A ``--model`` Option.
3. A loop that calls ``_validate_dial`` for each name/value pair.
4. Calls to ``_resolve_settings`` and ``_resolve_model_or_exit``.
5. A lazy import of the implementation, then a ``try / except`` that
   collapses any exception to ``typer.echo("tab: <reason>", err=True)``
   plus ``raise typer.Exit(1)``.

Eight verbs, ~50 lines of repetition each. The helper here pulls the
repeated half — dials + resolution + error contract — into one place,
leaving each subcommand body free to focus on its actual job
(positional args + lazy import + dispatch + stdout).

Two pieces:

- :class:`TabContext` — the resolved bundle yielded into a subcommand
  body. ``settings`` is the merged :class:`TabSettings`; ``model`` is
  the resolved model identifier (a non-empty string by the time the
  body sees it).
- :func:`personality_command` — a decorator that registers a
  Typer-shaped wrapper around a body function whose signature is
  ``(ctx: TabContext, *positional_args) -> None``. The wrapper exposes
  the dial Options + ``--model`` + the body's positional arguments to
  Typer's introspection, then runs validation, settings/model
  resolution, and the error wrapper before delegating to the body.

Why a decorator and not a context manager: a context manager would
still leave each subcommand declaring the five dial Options + ``--model``
in its own signature, which is the bulk of the repetition. The
decorator rewrites the wrapper's signature so the dial+model surface
is declared exactly once. The body's positional arguments
(``prompt: str``, ``request: list[str] | None``, etc.) are spliced in
front of the dials so ``tab ask --help`` still shows ``PROMPT`` as a
positional argument followed by the optional flags.

Why this fits Typer: Typer reads ``__signature__`` and the resolved
type annotations at registration time. We construct a wrapper whose
``__signature__`` and ``__annotations__`` carry the body's positionals
plus the dial+model Options, so ``tab ask --help`` renders exactly the
same surface as the hand-written version, and Typer's runtime dispatch
parses the same flags.

The error contract — one ``tab: <reason>`` line on stderr plus exit
code 1 — is preserved verbatim. Tests pin both halves; both halves
land here untouched.
"""

from __future__ import annotations

import inspect
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from functools import wraps
from typing import Any

import typer

from tab_cli.personality import TabSettings


# Names of the five personality dials, in display order. Adding a sixth
# dial means appending to this tuple and adding the matching field to
# :class:`TabSettings`. The dial Option block, the validation loop, and
# the resolver all read this tuple, so they stay in sync without a
# fanned-out edit.
DIAL_NAMES: tuple[str, ...] = (
    "humor",
    "directness",
    "warmth",
    "autonomy",
    "verbosity",
)


def _dial_options() -> dict[str, typer.models.OptionInfo]:
    """Return one ``--<dial> INT`` Option per personality dial.

    The help text and defaults stay identical across every subcommand
    that takes the dial surface — defining the Options here once means
    a wording tweak ripples through every command without an eight-site
    edit. Each Option is ``int | None``: ``None`` means the user didn't
    pass the flag, which the resolver reads as "fall through to the
    next layer" (config file, then :class:`TabSettings` defaults).
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
        for name in DIAL_NAMES
    }


DIAL_OPTS: dict[str, typer.models.OptionInfo] = _dial_options()


def model_option(
    help_text: str = (
        "pydantic-ai model name in <provider:model> form "
        "(e.g. anthropic:claude-sonnet-4)."
    ),
) -> typer.models.OptionInfo:
    """Return a ``--model`` Option with the given help text.

    Most commands use the default phrasing. ``tab mcp`` overrides it to
    note that per-call ``model`` arguments on ``ask_tab`` win over the
    server-startup default; the bare-``tab``/``chat`` callbacks override
    it to mention the chat REPL specifically. The help text is the only
    thing that varies — the parsing semantics (``str | None``,
    ``show_default=False``) are fixed.
    """
    return typer.Option(
        None,
        "--model",
        help=help_text,
        show_default=False,
    )


def validate_dial(name: str, value: int | None) -> None:
    """Range-check one personality flag. Exit non-zero on failure.

    The error format ``"<dial> must be 0-100, got <value>"`` is part of
    the CLI's contract — tests pin it. We deliberately don't use
    Typer's ``BadParameter`` wrapper here because that prepends
    ``Usage: ... Error:`` framing, which is hostile in a shell-out
    context (``tab ask --humor 150 ... || handle``). Same instinct as
    the runtime-error path: collapse to one stderr line and exit
    non-zero.
    """
    if value is None:
        return
    if not 0 <= value <= 100:
        typer.echo(f"{name} must be 0-100, got {value}", err=True)
        raise typer.Exit(code=1)


def validate_dials(values: dict[str, int | None]) -> None:
    """Run :func:`validate_dial` over every dial in :data:`DIAL_NAMES`."""
    for name in DIAL_NAMES:
        validate_dial(name, values.get(name))


def resolve_settings(dials: dict[str, int | None]) -> TabSettings:
    """Layer flag values on top of the config file, falling through to
    :class:`TabSettings` defaults.

    Per the settings-system synthesis (task 01KQ2YXEDHVD2YG1DPD9HEVR2S):
    flag > config file > tab.md defaults. Flags win for the whole
    invocation; anything still unset comes from
    ``~/.tab/config.toml``; anything still unset uses
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

    # Start with config-file values (whichever passed validation), then
    # let any explicitly-passed flag win. Unset flags (``None``) don't
    # appear in the merged dict, so :class:`TabSettings`'s field
    # defaults fill the rest.
    merged: dict[str, int] = dict(load_settings_from_config())
    for name in DIAL_NAMES:
        value = dials.get(name)
        if value is not None:
            merged[name] = value

    return TabSettings(**merged)


@dataclass(frozen=True)
class TabContext:
    """Resolved settings + model bundle yielded into a subcommand body.

    ``settings`` is the merged :class:`TabSettings` (flag > config >
    defaults). ``model`` is the resolved pydantic-ai model identifier
    — a non-empty string by the time the body sees it; the resolver
    has already exited the process if neither flag nor config produced
    one.
    """

    settings: TabSettings
    model: str


# A subcommand body has shape ``(ctx: TabContext, *positional) -> None``.
# Typer-aware kwargs (dial flags + ``--model``) are absorbed by the
# wrapper and never leak into the body's argument list — the body only
# sees the resolved bundle.
SubcommandBody = Callable[..., None]


def _build_wrapper_signature(
    body: SubcommandBody,
    *,
    model_help: str,
) -> inspect.Signature:
    """Splice the body's positional params in front of the dial+model
    Options, returning a signature Typer can introspect.

    The body's signature is ``(ctx: TabContext, *positional)`` — we
    drop ``ctx`` (the wrapper produces it) and keep every other
    parameter as-is, then append ``model`` and the five dials with
    their default :class:`typer.models.OptionInfo` defaults so Typer
    treats them as command-line flags. Order matters: positional
    arguments must come before keyword-only options or Typer's help
    text places them oddly.
    """
    body_sig = inspect.signature(body)
    body_params = [
        p for name, p in body_sig.parameters.items() if name != "ctx"
    ]

    options: list[inspect.Parameter] = []
    options.append(
        inspect.Parameter(
            "model",
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
            default=model_option(model_help),
            annotation=str | None,
        )
    )
    for name in DIAL_NAMES:
        options.append(
            inspect.Parameter(
                name,
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
                default=DIAL_OPTS[name],
                annotation=int | None,
            )
        )

    return body_sig.replace(parameters=[*body_params, *options])


def personality_command(
    app: typer.Typer,
    name: str,
    *,
    model_help: str | None = None,
) -> Callable[[SubcommandBody], SubcommandBody]:
    """Register a Typer subcommand whose body takes a :class:`TabContext`.

    The decorated function is the body of the subcommand. It must
    accept ``ctx: TabContext`` as its first parameter, then any
    positional arguments the verb owns (e.g. ``prompt: str`` for
    ``ask``, ``request: list[str] | None`` for ``draw-dino``). The
    decorator builds a Typer-registered wrapper that:

    1. Exposes ``--model`` + the five dial flags on the Typer surface,
       in addition to the body's positional arguments.
    2. Runs :func:`validate_dials` over the dial values (so an
       out-of-range value exits with the contract'd one-line error
       *before* any subcommand work starts).
    3. Resolves :class:`TabSettings` and the model identifier via
       :func:`resolve_settings` and ``_resolve_model_or_exit``.
    4. Calls the body with the resolved :class:`TabContext` plus the
       positional arguments, inside a ``try`` whose ``except`` collapses
       any exception to ``typer.echo("tab: <reason>", err=True); raise
       typer.Exit(1)``.

    The model help text defaults to the generic per-command phrasing.
    Override via ``model_help`` for subcommands like ``mcp`` whose
    flag has a different meaning ("default model for the MCP server").

    The model resolver is looked up on :mod:`tab_cli.cli` at *call*
    time, not at import time, so the suite-wide test fixture that
    monkeypatches ``tab_cli.cli._resolve_model_or_exit`` keeps
    working.
    """
    final_model_help = model_help

    def _decorate(body: SubcommandBody) -> SubcommandBody:
        wrapper_sig = _build_wrapper_signature(
            body,
            model_help=final_model_help
            or (
                "pydantic-ai model name in <provider:model> form "
                "(e.g. anthropic:claude-sonnet-4)."
            ),
        )

        # Names of the body's positional parameters, in declaration
        # order, minus ``ctx``. The wrapper unpacks the bound arguments
        # by name and forwards these into the body.
        positional_names = [
            pname for pname in inspect.signature(body).parameters if pname != "ctx"
        ]

        @wraps(body)
        def _wrapper(*args: Any, **kwargs: Any) -> None:
            bound = wrapper_sig.bind(*args, **kwargs)
            bound.apply_defaults()
            arguments = bound.arguments

            dials = {dname: arguments.get(dname) for dname in DIAL_NAMES}
            validate_dials(dials)

            settings = resolve_settings(dials)
            model = _resolve_model_via_cli(arguments.get("model"))
            ctx = TabContext(settings=settings, model=model)

            try:
                body(
                    ctx,
                    *(arguments[pname] for pname in positional_names),
                )
            except Exception as exc:  # noqa: BLE001 — collapse to readable error
                # Typer's default behavior on uncaught exceptions is a
                # traceback dump, which is hostile in a shell-out / CI
                # context. We collapse to a one-line stderr message and
                # a non-zero exit so callers can do the usual
                # ``|| handle`` shell idiom.
                typer.echo(f"tab: {exc}", err=True)
                raise typer.Exit(code=1) from exc

        # Typer reads the wrapper's ``__signature__`` and
        # ``__annotations__`` to build the command's argument and
        # option surface. ``functools.wraps`` already copied the body's
        # name + docstring (so ``tab <verb> --help`` shows the body's
        # docstring); we overwrite the signature here so Typer sees the
        # spliced positional + Option layout instead of the body's
        # ``(ctx, ...)`` shape.
        _wrapper.__signature__ = wrapper_sig  # type: ignore[attr-defined]
        _wrapper.__annotations__ = {
            param.name: param.annotation
            for param in wrapper_sig.parameters.values()
            if param.annotation is not inspect.Parameter.empty
        }

        app.command(name)(_wrapper)
        return _wrapper

    return _decorate


def _resolve_model_via_cli(flag_value: str | None) -> str:
    """Resolve the model string by routing through :mod:`tab_cli.cli`.

    The suite-wide ``conftest.py`` autouse fixture monkeypatches
    ``tab_cli.cli._resolve_model_or_exit`` to a stub that returns the
    flag value when set or ``"anthropic:test-stub"`` otherwise. We
    look up the resolver on the ``cli`` module at call time so the
    patched version wins — importing and binding it at module load
    would freeze the production resolver and skip the patch.
    """
    from tab_cli import cli

    return cli._resolve_model_or_exit(flag_value)


def error_wrapped(func: Callable[..., None]) -> Callable[..., None]:
    """Wrap a function in the ``tab: <reason>`` / exit-1 error contract.

    Used by the few subcommands that don't take the personality dial
    surface (``setup``, the ``grimoire`` triplet) but still want the
    same one-line stderr-and-exit-1 collapse on exceptions. Pure
    error-shape sugar — no settings or model resolution.
    """

    @wraps(func)
    def _wrapper(*args: Any, **kwargs: Any) -> None:
        try:
            func(*args, **kwargs)
        except typer.Exit:
            # Already shaped — let Typer's exit machinery handle it.
            raise
        except Exception as exc:  # noqa: BLE001
            typer.echo(f"tab: {exc}", err=True)
            raise typer.Exit(code=1) from exc

    return _wrapper


def join_words(words: Iterable[str] | None) -> str:
    """Concatenate positional args into a single user prompt string.

    Three of the personality-skill ports (``draw-dino``, ``listen``,
    ``think``, ``teach``) take a free-form ``[REQUEST]...`` /
    ``[TOPIC]...`` / ``[IDEA]...`` positional that Typer hands back as
    a list of strings. The skills accept the joined-with-spaces form,
    or an empty string if the user passed no positional. This helper
    handles both branches in one line so the subcommand bodies don't
    repeat the ``" ".join(x) if x else ""`` ternary.
    """
    if not words:
        return ""
    return " ".join(words)
