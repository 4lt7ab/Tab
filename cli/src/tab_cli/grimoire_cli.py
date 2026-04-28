"""Typer subcommand group for ``tab grimoire``.

``tab grimoire`` is the user-facing override surface for the
personality-skill registry's per-item thresholds. Three subcommands —
``set``, ``reset``, ``show`` — read and write a tiny JSON store at
``~/.tab/grimoire-overrides.json``. The store and its
settings-system migration debt live in :mod:`tab_cli.grimoire_overrides`.

Per the design synthesis (task 01KQ2YXEDJFXCJCFTERK6WFZW9), this
command does not adjust SKILL.md frontmatter values — the
author-default lives there, and the CLI's job is the override layer.
The frontmatter loader changes are a separate ticket; until those
land, every skill's source-of-value reads as ``loader-default`` or
``override`` and never ``frontmatter``.

This module exports :data:`grimoire_app`, a :class:`typer.Typer`
sub-app that the top-level ``tab`` app mounts via ``add_typer``. Each
subcommand uses the shared ``tab: <reason>`` / exit-1 error contract
from :mod:`tab_cli.commands`.
"""

from __future__ import annotations

import typer

grimoire_app = typer.Typer(
    name="grimoire",
    help=(
        "Inspect and override grimoire's per-skill matching thresholds. "
        "Subcommands: set, reset, show."
    ),
    no_args_is_help=True,
    add_completion=False,
)


def _load_registry_for_show() -> "object":
    """Build the registry without forcing a real grimoire gate.

    ``tab grimoire show`` only needs the parsed :class:`SkillRecord`
    list — the gate is irrelevant. We construct a no-op ``Gate`` stand-in
    by re-implementing the loader's frontmatter walk inline rather than
    calling :func:`tab_cli.registry.load_skill_registry`, which would
    pull in pgvector/Ollama at import time. The returned object has the
    same ``records`` shape :func:`effective_thresholds` expects.
    """
    from tab_cli.paths import plugins_dir
    from tab_cli.registry import parse_skill_frontmatter

    skills_dir = plugins_dir() / "tab" / "skills"
    if not skills_dir.is_dir():
        raise FileNotFoundError(
            f"expected personality skills directory at {skills_dir}",
        )

    skill_md_paths = sorted(skills_dir.glob("*/SKILL.md"))
    records = tuple(parse_skill_frontmatter(path) for path in skill_md_paths)

    # Lightweight stand-in mirroring SkillRegistry's read-only surface:
    # only ``records`` is consumed by the show command, so we don't
    # need a real Gate.
    class _RegistrySnapshot:
        def __init__(self, records: tuple) -> None:
            self.records = records

    return _RegistrySnapshot(records)


@grimoire_app.command("set")
def grimoire_set(
    skill: str = typer.Argument(
        ...,
        help="Name of the skill whose threshold should be overridden.",
        show_default=False,
    ),
    threshold: float = typer.Argument(
        ...,
        help="New threshold value in [0.0, 1.0]. Higher = stricter match.",
        show_default=False,
    ),
) -> None:
    """Override the matching threshold for a skill.

    Writes a row into ``~/.tab/grimoire-overrides.json`` (the
    v0 store; this migrates into the settings-system file when that
    ticket lands). Values must be in ``[0.0, 1.0]``; the rest of the
    error contract matches every other ``tab`` subcommand — collapse
    to one stderr line, exit non-zero.
    """
    from tab_cli.grimoire_overrides import OverrideError, set_override

    try:
        set_override(skill, threshold)
    except OverrideError as exc:
        typer.echo(f"tab: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    except OSError as exc:
        typer.echo(f"tab: could not write override: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    typer.echo(f"set {skill} threshold to {threshold}")


@grimoire_app.command("reset")
def grimoire_reset(
    skill: str = typer.Argument(
        ...,
        help="Name of the skill whose override should be cleared.",
        show_default=False,
    ),
) -> None:
    """Clear the override for a skill; the effective threshold reverts.

    A reset against a skill that has no override is not an error —
    the command prints a one-line note and exits 0, so re-running
    ``tab grimoire reset draw-dino`` is idempotent. The effective
    value falls back to the SKILL.md frontmatter default if one is
    declared (after the loader-side ticket lands), otherwise to the
    loader's single default constant.
    """
    from tab_cli.grimoire_overrides import OverrideError, reset_override

    try:
        removed = reset_override(skill)
    except OverrideError as exc:
        typer.echo(f"tab: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    except OSError as exc:
        typer.echo(f"tab: could not write override: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    if removed:
        typer.echo(f"reset {skill}")
    else:
        typer.echo(f"no override set for {skill}")


@grimoire_app.command("show")
def grimoire_show() -> None:
    """Print every loaded skill with its effective threshold and source.

    Output is one row per skill: ``<name>\\t<threshold>\\t<source>``.
    Source is one of ``override``, ``frontmatter``, or ``loader-default``
    — see :func:`tab_cli.grimoire_overrides.effective_thresholds` for
    the layering rules.
    """
    from tab_cli.grimoire_overrides import (
        OverrideError,
        effective_thresholds,
        load_overrides,
    )

    try:
        registry = _load_registry_for_show()
    except (FileNotFoundError, OSError) as exc:
        typer.echo(f"tab: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    except Exception as exc:  # noqa: BLE001 — collapse to readable error
        typer.echo(f"tab: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    try:
        overrides = load_overrides()
    except OverrideError as exc:
        typer.echo(f"tab: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    rows = effective_thresholds(registry.records, overrides)
    if not rows:
        typer.echo("no skills loaded")
        return

    # Plain TSV. The format is intentionally simple — easy to grep,
    # easy to pipe into ``column -t``, and stable across any future
    # rich-table reshaping (which would land in its own ticket).
    for row in rows:
        typer.echo(f"{row.name}\t{row.threshold}\t{row.source}")
