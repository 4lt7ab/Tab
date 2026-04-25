"""``tab setup`` — print the CLI install / provider-key cheat sheet.

The body is a checked-in markdown file (:mod:`tab_cli` ships ``setup.md``
alongside this module) that the subcommand reads and prints verbatim.
Same substrate principle as :mod:`tab_cli.personality` and
:mod:`tab_cli.skills`: prose lives in markdown, Python is plumbing.

Reading off disk on every invocation is intentional. The block is short,
the cost of a single :meth:`Path.read_text` is negligible next to Typer
startup, and a stale in-memory copy would silently drift if a future
edit to ``setup.md`` lands without a process restart. Same trade
:func:`tab_cli.skills.read_skill_body` makes for the same reasons.
"""

from __future__ import annotations

from pathlib import Path


def _setup_md_path() -> Path:
    """Return the on-disk location of the ``setup.md`` body.

    Co-located with this module so ``hatchling`` picks it up as part of
    the wheel — the default include rule for ``packages = ["src/tab_cli"]``
    bundles every file under that tree, including markdown.
    """
    return Path(__file__).resolve().parent / "setup.md"


def read_setup_body() -> str:
    """Return the verbatim contents of ``setup.md``.

    No frontmatter handling — ``setup.md`` is plain prose, not a SKILL
    file. Trailing newline (if any) is preserved so the printed block
    ends cleanly.
    """
    return _setup_md_path().read_text(encoding="utf-8")
