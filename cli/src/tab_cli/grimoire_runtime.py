"""Process-once migrate-on-first-use guard for grimoire-core.

grimoire-core ships a hand-rolled :class:`MigrationRunner` (idempotent,
tracked in a ``_migrations`` SQLite table) but does not auto-run on
``Gate``/``Curator`` construction. Tab is the embedding host: the
schema needs to exist before the first ``match`` or ``add_item``, so
*we* own running the migrations.

The strategy is migrate-on-first-use, not migrate-on-import. Reasons:

* ``tab --help`` and the personality-only verbs (``tab draw-dino``)
  never touch grimoire and shouldn't pay DB I/O on every invocation.
* The five subcommands that *do* touch grimoire (``tab chat``,
  ``tab ask``, ``tab muse``, plus the chat-routed skills) all funnel
  through :meth:`grimoire_core.Gate.from_settings` /
  :meth:`grimoire_core.Curator.from_settings`. Calling
  :func:`ensure_migrated` immediately before those constructors is
  the narrowest hook that still covers every real call site.

This module also pins the grimoire DB path to ``~/.tab/grimoire.db``
when the user hasn't set one explicitly. grimoire-core's own default
is cwd-relative (``.grimoire/database/grimoire.db``), which would
fragment state across every directory the user ran ``tab`` from. We
funnel onto the same ``~/.tab/`` directory that already holds
:mod:`tab_cli.config`'s ``config.toml`` and
:mod:`tab_cli.grimoire_overrides`'s ``grimoire-overrides.json``.

Tests bypass this helper for free: the ``gate=`` / ``curator=`` test
seams in :func:`tab_cli.registry.load_skill_registry` and
:func:`tab_cli.muse.run_muse` skip the ``from_settings`` branch
entirely, which is also where :func:`ensure_migrated` lives.
"""

from __future__ import annotations

import os
from functools import cache
from pathlib import Path


def _default_database_url() -> str:
    """Resolve the Tab-default grimoire DB path: ``~/.tab/grimoire.db``.

    grimoire-core auto-creates parent directories on first open, so we
    don't ``mkdir`` here — the URL alone is enough. Lives alongside the
    other ``~/.tab/`` user-state files so a single rm of that dir wipes
    every Tab artifact in one shot.
    """
    return f"sqlite:///{Path.home() / '.tab' / 'grimoire.db'}"


def _pin_database_url() -> None:
    """Set ``GRIMOIRE_DATABASE_URL`` to the Tab-default if unset.

    Must run before grimoire-core's :func:`get_settings` is called for
    the first time — that function is ``lru_cache``-d, so the env var
    we set here is read once at first construction and locked in. Any
    later edit to the env var would be silently ignored. The ordering
    contract: this runs at the top of :func:`ensure_migrated`, which
    every settings-backed grimoire call site invokes before any
    ``from_settings`` constructor.

    Uses ``setdefault`` so a user who has explicitly exported
    ``GRIMOIRE_DATABASE_URL`` still wins — handy for pointing
    integration tests or one-off shells at a scratch DB.
    """
    os.environ.setdefault("GRIMOIRE_DATABASE_URL", _default_database_url())


@cache
def ensure_migrated() -> tuple[str, ...]:
    """Apply every pending grimoire migration exactly once per process.

    Returns the ids of migrations applied on the *first* call —
    typically empty after the schema lands, non-empty on a fresh DB
    or after a grimoire-core upgrade. Subsequent calls return the
    cached tuple without touching the DB; the runner's own tracking
    table makes that a correctness guarantee, the cache just avoids
    the round-trip.

    Pins the DB path before importing the runner so grimoire-core's
    settings-cache reads the Tab-default location, not its own
    cwd-relative fallback. Construction is otherwise lazy on purpose:
    importing :class:`grimoire_core.migrations.MigrationRunner` pulls
    in the sqlite-vec-loaded connection and the embedder settings
    stack, and we want both deferred until a caller actually intends
    to talk to the DB.
    """
    _pin_database_url()

    from grimoire_core.migrations import MigrationRunner

    return MigrationRunner().up()
