"""Shared filesystem and frontmatter helpers for the Tab CLI.

This module exists to kill a 4-site duplication of the same
"walk up four levels from this file, then into ``plugins/``" derivation
and a 3-site duplication of the YAML-frontmatter stripper. The earlier
read was that "one duplicated copy is the cheaper trade than a third
shared frontmatter utility module" (see the comment that used to live in
``skills.py``). That trade flipped the moment the registry's stricter
parser became the third copy and ``cli.py`` joined as the fourth
plugins-dir derivation — five separate places that had to stay in sync
on a layout assumption (``cli/src/tab_cli/<file>.py`` is four levels
deep from the repo root) and on what counts as a well-formed
frontmatter fence.

Consolidated sites:

- :func:`plugins_dir` replaces the inline derivations in
  ``cli/src/tab_cli/cli.py`` (``_load_registry_for_show``),
  ``cli/src/tab_cli/chat.py`` (``run_chat``'s default-registry branch),
  ``cli/src/tab_cli/skills.py`` (``_default_plugins_dir``), and
  ``cli/src/tab_cli/personality.py`` (``_repo_root`` / ``_tab_md_path``).
- :func:`parse_frontmatter` replaces the strict parser at
  ``cli/src/tab_cli/registry.py`` (``_extract_frontmatter``); it is the
  authoritative shape and is now also the basis for
  :func:`strip_frontmatter`, which replaces the byte-identical lenient
  strippers at ``cli/src/tab_cli/personality.py`` and
  ``cli/src/tab_cli/skills.py``.

Two frontmatter helpers, not one:

- :func:`parse_frontmatter` returns ``(frontmatter_dict, body)`` and
  raises :class:`FrontmatterError` on a missing, unclosed, or non-mapping
  fence. Used by the registry, where startup-time validation of
  ``SKILL.md`` is load-bearing — a silently-skipped skill makes the agent
  feel mysteriously unresponsive.
- :func:`strip_frontmatter` returns the body only and is lenient: a file
  without a fence (or with an unterminated one) passes through unchanged.
  Used by ``personality.py`` and ``skills.py``, where the markdown body
  is the prompt and the frontmatter is metadata the registry has
  already vetted.

Splitting the two preserves both call-site shapes (``body = strip(...)``
vs ``meta, _ = parse(...)``) without forcing one caller to discard half
the result tuple every time. The leniency split is real, not cosmetic:
the registry refuses bad fences, the prompt-loaders survive them.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml


class FrontmatterError(ValueError):
    """A Markdown file's YAML frontmatter is missing or malformed.

    Raised by :func:`parse_frontmatter`. The registry re-exports this as
    :class:`tab_cli.registry.SkillFrontmatterError` so existing callers
    that catch the registry-shaped name keep working; new code can catch
    either.
    """


_REPO_ROOT_DEPTH = 4
"""How many ``.parent`` hops separate this file from the repo root.

``cli/src/tab_cli/paths.py`` lives four levels deep:
``paths.py`` → ``tab_cli/`` → ``src/`` → ``cli/`` → repo root. Named so
the math reads like the layout, not like an off-by-one puzzle.
"""


@lru_cache(maxsize=1)
def plugins_dir() -> Path:
    """Return ``<repo>/plugins`` derived from this file's location.

    Cached because the answer is fixed for the lifetime of the process
    and every personality / registry / chat init touches it.
    """
    here = Path(__file__).resolve()
    repo_root = here
    for _ in range(_REPO_ROOT_DEPTH):
        repo_root = repo_root.parent
    return repo_root / "plugins"


@lru_cache(maxsize=1)
def cli_skills_dir() -> Path:
    """Return the CLI-local skills directory: ``cli/src/tab_cli/skills``.

    Companion to :func:`plugins_dir`. Skills shared with the Claude
    Code plugin host live under ``plugins/tab/skills/``; skills whose
    capability depends on CLI-only Python (grimoire-core, the settings
    system, anything pydantic-ai-shaped) live here. The registry
    loader walks both paths and seeds them into a single gate, so a
    chat turn matches across the union without callers caring which
    home a given skill came from.

    Cached for the same reason :func:`plugins_dir` is — fixed for the
    lifetime of the process, touched every chat / ask init.
    """
    return Path(__file__).resolve().parent / "skills"


def parse_frontmatter(text: str, path: Path) -> tuple[dict[str, object], str]:
    """Pull the YAML frontmatter and body out of a Markdown file.

    Frontmatter is the standard Jekyll-shaped fence: a leading ``---`` on
    its own line, a trailing ``---`` on its own line, YAML in between.
    Anything else (no fence, single fence, non-mapping content) raises
    :class:`FrontmatterError` with ``path`` keyed in the message so the
    surface error names the offending file.

    Returns ``(frontmatter_dict, body)``; ``body`` has its leading blank
    lines trimmed so callers can splice it into a prompt without an
    awkward gap.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise FrontmatterError(
            f"{path}: file does not start with a '---' frontmatter fence",
        )

    closing_index: int | None = None
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            closing_index = index
            break

    if closing_index is None:
        raise FrontmatterError(
            f"{path}: frontmatter fence is not closed",
        )

    yaml_block = "\n".join(lines[1:closing_index])
    try:
        parsed = yaml.safe_load(yaml_block)
    except yaml.YAMLError as exc:
        raise FrontmatterError(
            f"{path}: frontmatter is not valid YAML ({exc})",
        ) from exc

    if not isinstance(parsed, dict):
        raise FrontmatterError(
            f"{path}: frontmatter must be a YAML mapping, "
            f"got {type(parsed).__name__}",
        )

    body = "\n".join(lines[closing_index + 1 :]).lstrip("\n")
    return parsed, body


def strip_frontmatter(text: str) -> str:
    """Return ``text`` with a leading ``--- ... ---`` fence removed.

    Lenient by design: a file without a fence (or with an unterminated
    one) passes through unchanged rather than raising. The strict variant
    — :func:`parse_frontmatter` — is what the registry uses to validate
    a ``SKILL.md`` at load time; by the time a prompt-loader runs, the
    file is known well-formed enough to register and a torn-write
    halfway through dispatch shouldn't be more disruptive than a stale
    body would.

    Returns the body with leading blank lines trimmed so the caller can
    splice it into a prompt without an awkward gap.
    """
    if not text.startswith("---"):
        return text

    lines = text.splitlines(keepends=True)
    if not lines or lines[0].rstrip("\r\n") != "---":
        return text

    for idx in range(1, len(lines)):
        if lines[idx].rstrip("\r\n") == "---":
            body = "".join(lines[idx + 1 :])
            return body.lstrip("\n")

    # Unterminated fence — fall back to the whole text.
    return text
