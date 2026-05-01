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
        "Inspect and override grimoire state. "
        "Threshold overrides: set, reset, show. "
        "Database inspection: list, items, explain."
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

    Walks both skill homes (plugin tree + CLI-local) in the same order
    :func:`tab_cli.registry.load_skill_registry` does, so the show
    output is the same set of records the chat REPL gates against.
    """
    from tab_cli.paths import cli_skills_dir, plugins_dir
    from tab_cli.registry import parse_skill_frontmatter

    plugin_skills_dir = plugins_dir() / "tab" / "skills"
    if not plugin_skills_dir.is_dir():
        raise FileNotFoundError(
            f"expected personality skills directory at {plugin_skills_dir}",
        )

    skill_md_paths = sorted(plugin_skills_dir.glob("*/SKILL.md"))
    cli_dir = cli_skills_dir()
    if cli_dir.is_dir():
        skill_md_paths.extend(sorted(cli_dir.glob("*/SKILL.md")))
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


# --------------------------------------------------------- DB inspection
#
# The three commands below — ``list``, ``items``, ``explain`` — read
# straight from the grimoire-core SQLite store at ``~/.tab/grimoire.db``
# (pinned by :mod:`tab_cli.grimoire_runtime`). They share a TSV-shaped
# output convention with ``show``: one row per record, no header, no
# rich tables. ``column -t`` is the canonical pretty-printer.
#
# Each command runs migrations first via ``ensure_migrated`` so a fresh
# install can ``tab grimoire list`` without going through chat/ask
# first to materialise the schema.


@grimoire_app.command("list")
def grimoire_list() -> None:
    """List every corpus in the grimoire DB with item count and embedder.

    Output is one row per corpus:
    ``<corpus_key>\\t<item_count>\\t<embedder>\\t<dimensions>\\t<embedded_at>``.
    Empty database prints "no corpora".

    The embedder/dimensions/embedded_at columns come from
    ``corpus_meta`` and are present iff the corpus has ever been
    written. ``-`` is shown when grimoire has the corpus key but no
    meta row (shouldn't happen in normal flows; surfaces as ``-`` so
    you can see it instead of crashing on a None format).
    """
    from tab_cli.grimoire_runtime import ensure_migrated

    try:
        ensure_migrated()
        from grimoire_core import list_corpora

        corpora = list_corpora()
    except Exception as exc:  # noqa: BLE001 — collapse to readable error
        typer.echo(f"tab: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    if not corpora:
        typer.echo("no corpora")
        return

    for corpus in sorted(corpora, key=lambda c: c.corpus_key):
        embedder = corpus.embedder or "-"
        dims = corpus.embedding_dimensions if corpus.embedding_dimensions is not None else "-"
        embedded_at = corpus.embedded_at or "-"
        typer.echo(
            f"{corpus.corpus_key}\t{corpus.item_count}\t{embedder}\t{dims}\t{embedded_at}",
        )


@grimoire_app.command("items")
def grimoire_items(
    corpus: str = typer.Argument(
        ...,
        help="Corpus key to dump (e.g. tab-cli-skills, topic:auth-rewrite).",
        show_default=False,
    ),
) -> None:
    """List every item in a corpus.

    Output is one row per item: ``<name>\\t<threshold>\\t<text>``. Sorted
    by name (matches grimoire-core's ``list_items`` order). Empty or
    unknown corpus prints "no items in <corpus>" — the two cases are
    not distinguished, since the user-visible answer is the same:
    nothing to look at.

    Reads only — no embedder is invoked, so this works without Ollama
    reachable. ``Curator.from_settings`` does construct an
    ``OllamaEmbedder`` lazily, but the embedder's network calls only
    fire on writes, which ``export()`` doesn't do.
    """
    from tab_cli.grimoire_runtime import ensure_migrated

    try:
        ensure_migrated()
        from grimoire_core import Curator

        items = Curator.from_settings(corpus).export()
    except Exception as exc:  # noqa: BLE001 — collapse to readable error
        typer.echo(f"tab: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    if not items:
        typer.echo(f"no items in {corpus}")
        return

    for item in items:
        typer.echo(f"{item.name}\t{item.threshold}\t{item.text}")


@grimoire_app.command("explain")
def grimoire_explain(
    corpus: str = typer.Argument(
        ...,
        help="Corpus key to query against.",
        show_default=False,
    ),
    query: list[str] = typer.Argument(
        ...,
        metavar="QUERY...",
        help=(
            "Natural-language query. Words are joined with single spaces "
            "and embedded as a search query."
        ),
        show_default=False,
    ),
    top_k: int = typer.Option(
        5,
        "--top-k",
        "-k",
        help="Number of neighbours to return (default 5).",
    ),
) -> None:
    """Show top-k neighbours for a query against a corpus.

    Output is one row per neighbour, sorted by similarity descending:
    ``<name>\\t<similarity>\\t<threshold>\\t<pass|fail>``. Similarity
    and threshold are formatted to three decimals; ``pass`` means the
    row would have fired through ``Gate.match``, ``fail`` means it
    would have stayed silent. Empty result (no rows in corpus, or
    ``--top-k 0``) prints "no neighbours".

    Unlike ``items``, this command embeds the query — Ollama needs to
    be reachable. If it isn't, the failure collapses to a readable
    ``tab: <reason>`` line just like the other subcommands.
    """
    if top_k < 0:
        typer.echo("tab: --top-k must be >= 0", err=True)
        raise typer.Exit(code=1)

    from tab_cli.commands import join_words
    from tab_cli.grimoire_runtime import ensure_migrated

    rendered_query = join_words(query)

    try:
        ensure_migrated()
        from grimoire_core import Gate

        gate = Gate.from_settings(corpus=corpus)
        hits = gate.explain(rendered_query, k=top_k)
    except Exception as exc:  # noqa: BLE001 — collapse to readable error
        typer.echo(f"tab: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    if not hits:
        typer.echo("no neighbours")
        return

    for hit in hits:
        flag = "pass" if hit.passed else "fail"
        typer.echo(
            f"{hit.name}\t{hit.similarity:.3f}\t{hit.threshold:.3f}\t{flag}",
        )
