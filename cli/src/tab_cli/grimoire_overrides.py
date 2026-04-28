"""User-level grimoire threshold overrides for the personality-skill registry.

The synthesis on task 01KQ2YXEDJFXCJCFTERK6WFZW9 picked combination
*D + B*: SKILL.md frontmatter holds the author-default, and a CLI
command sets a user override on top of it. This module owns the
override half — the persisted store, the read/write API, and the
"effective threshold + source" computation that ``tab grimoire show``
prints.

The frontmatter half shipped on the loader side
(task 01KQ32BB20G22GKBDHTEC6376B): :func:`tab_cli.registry.parse_skill_frontmatter`
reads ``grimoire-threshold`` and falls back to
:data:`tab_cli.registry.DEFAULT_THRESHOLD` when the key is absent.
``effective_thresholds`` reports ``frontmatter`` for any record whose
threshold diverges from that loader default, ``override`` when the
user has set one, and ``loader-default`` otherwise. The frontmatter
branch is dormant in practice today only because no SKILL.md
currently sets a non-default ``grimoire-threshold`` — the parser is
wired up and waiting.

Persistence shape — v0
-----------------------

The synthesis defers the durable shape of user state to the
settings-system design ticket (01KQ2YXEDHVD2YG1DPD9HEVR2S). Until that
lands, this module writes a tiny JSON file at
``~/.tab/grimoire-overrides.json`` (alongside :mod:`tab_cli.config`'s
``~/.tab/config.toml``):

.. code-block:: json

   {
     "version": 1,
     "thresholds": {
       "draw-dino": 0.45,
       "teach": 0.7
     }
   }

When settings-system lands, this store gets folded into the canonical
TOML (likely a ``[grimoire.thresholds]`` section per the synthesis).
The JSON file becomes legacy and a one-shot migration drops it.

TODO(settings-system 01KQ2YXEDHVD2YG1DPD9HEVR2S): replace the
JSON-on-disk path with whatever shape that ticket lands. That ticket
is the only remaining migration debt for this module.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from tab_cli.registry import SkillRecord


# Format version of the on-disk JSON. Bumped only when the shape
# changes incompatibly; readers tolerate older versions or warn.
_OVERRIDE_FORMAT_VERSION = 1


# Float bounds on a stored threshold. The grimoire gate does cosine
# similarity, which lives in [-1.0, 1.0] in theory but [0.0, 1.0] in
# practice for embedding models — and a negative threshold means
# "always pass," which is not a sensible user override. Bounding to
# [0, 1] inclusive matches the SKILL.md frontmatter contract from the
# synthesis.
_MIN_THRESHOLD = 0.0
_MAX_THRESHOLD = 1.0


# Source labels reported by :func:`effective_thresholds`. Kept as a
# Literal type so misspellings show up at type-check time.
ThresholdSource = Literal["override", "frontmatter", "loader-default"]


class OverrideError(ValueError):
    """A stored override or a user-supplied value failed validation.

    Raised loud rather than silently dropped: the override store is
    small and user-edited, and a malformed entry usually means a
    typo we want to surface (so a wrong-feeling threshold doesn't
    silently apply to nothing). The CLI catches this and collapses it
    to a single stderr line per the existing ``tab: <reason>`` pattern.
    """


@dataclass(frozen=True, slots=True)
class EffectiveThreshold:
    """One row of the ``tab grimoire show`` table.

    ``threshold`` is whatever the gate would currently use for this
    skill (override if present, else the SkillRecord's value).
    ``source`` names which layer that value came from.
    """

    name: str
    threshold: float
    source: ThresholdSource


def overrides_path() -> Path:
    """Resolve the v0 overrides file path: ``~/.tab/grimoire-overrides.json``.

    Lives alongside :mod:`tab_cli.config`'s ``~/.tab/config.toml`` so all
    Tab user state stays under one directory. The XDG_CONFIG_HOME env
    var is intentionally not honored — Tab uses the dotfile-style
    ``~/.<app>/`` layout (see :mod:`tab_cli.config` for rationale).
    """
    return Path.home() / ".tab" / "grimoire-overrides.json"


def load_overrides(path: Path | None = None) -> dict[str, float]:
    """Read the per-skill threshold overrides from disk.

    Missing file is fine — returns an empty dict, no warning. A
    malformed file raises :class:`OverrideError` so the CLI can
    surface the broken state instead of silently ignoring user
    config; the user almost certainly wants to know they typoed
    something. Out-of-range thresholds inside an otherwise-valid file
    raise the same way: better to refuse the load than to silently
    drop one row from a hand-edited file.

    The optional ``path`` argument is a test seam; production callers
    use :func:`overrides_path`.
    """
    target = path if path is not None else overrides_path()

    try:
        raw = target.read_bytes()
    except FileNotFoundError:
        return {}
    except OSError as exc:
        raise OverrideError(f"could not read {target}: {exc}") from exc

    try:
        decoded = json.loads(raw.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise OverrideError(f"malformed override file {target}: {exc}") from exc

    if not isinstance(decoded, dict):
        raise OverrideError(
            f"override file {target} must hold a JSON object at the top level",
        )

    thresholds = decoded.get("thresholds", {})
    if not isinstance(thresholds, dict):
        raise OverrideError(
            f"override file {target}: 'thresholds' must be a JSON object",
        )

    result: dict[str, float] = {}
    for name, value in thresholds.items():
        if not isinstance(name, str) or not name.strip():
            raise OverrideError(
                f"override file {target}: skill name must be a non-empty string, "
                f"got {name!r}",
            )
        # bool is a subclass of int — reject it explicitly so a
        # ``"draw-dino": true`` doesn't sneak through as 1.0.
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise OverrideError(
                f"override file {target}: threshold for {name!r} must be a number, "
                f"got {value!r}",
            )
        threshold = float(value)
        if not _MIN_THRESHOLD <= threshold <= _MAX_THRESHOLD:
            raise OverrideError(
                f"override file {target}: threshold for {name!r} must be in "
                f"[{_MIN_THRESHOLD}, {_MAX_THRESHOLD}], got {threshold}",
            )
        result[name] = threshold

    return result


def save_overrides(values: dict[str, float], path: Path | None = None) -> None:
    """Write the override table back to disk.

    Creates the parent directory if needed (the user may not have run
    anything else that writes to ``~/.tab/`` yet). Writes
    pretty-printed JSON with sorted keys so a hand-edit-then-CLI-write
    round-trip produces a stable diff.
    """
    target = path if path is not None else overrides_path()
    target.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "version": _OVERRIDE_FORMAT_VERSION,
        "thresholds": dict(sorted(values.items())),
    }
    target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def set_override(name: str, threshold: float, path: Path | None = None) -> None:
    """Persist a single ``name -> threshold`` override.

    Validation matches :func:`load_overrides`: the name must be a
    non-empty string, the threshold must be a real number in
    ``[0.0, 1.0]``. The store is a read-modify-write of the JSON file
    — small enough that a write lock isn't worth the complexity for a
    hobby CLI.
    """
    if not isinstance(name, str) or not name.strip():
        raise OverrideError("skill name must be a non-empty string")
    if isinstance(threshold, bool) or not isinstance(threshold, (int, float)):
        raise OverrideError(
            f"threshold must be a number, got {threshold!r}",
        )
    threshold_value = float(threshold)
    if not _MIN_THRESHOLD <= threshold_value <= _MAX_THRESHOLD:
        raise OverrideError(
            f"threshold for {name!r} must be in "
            f"[{_MIN_THRESHOLD}, {_MAX_THRESHOLD}], got {threshold_value}",
        )

    current = load_overrides(path=path)
    current[name.strip()] = threshold_value
    save_overrides(current, path=path)


def reset_override(name: str, path: Path | None = None) -> bool:
    """Remove the override for ``name``. Returns ``True`` if a row was removed.

    Returning a bool instead of raising on a missing-key reset keeps
    ``tab grimoire reset`` idempotent: re-running the same reset is
    fine, and the CLI can choose how to phrase the "nothing was
    overridden" case (a one-line note rather than an error).
    """
    if not isinstance(name, str) or not name.strip():
        raise OverrideError("skill name must be a non-empty string")

    current = load_overrides(path=path)
    key = name.strip()
    if key not in current:
        return False
    current.pop(key)
    save_overrides(current, path=path)
    return True


def effective_thresholds(
    records: Iterable[SkillRecord],
    overrides: dict[str, float] | None = None,
    *,
    loader_default: float | None = None,
) -> list[EffectiveThreshold]:
    """Compose per-skill ``(name, threshold, source)`` rows for ``show``.

    Layering, top-to-bottom:

    1. Override (from the persisted store) wins.
    2. Otherwise, if the SkillRecord's threshold differs from the
       loader default, treat it as a frontmatter-author value. The
       loader-side parser already reads ``grimoire-threshold`` from
       SKILL.md frontmatter; this branch is dormant only because no
       SKILL.md currently sets a non-default value, and lights up the
       moment one does.
    3. Otherwise, the value came from the loader's single default
       constant.

    ``overrides`` defaults to whatever :func:`load_overrides` returns
    when omitted. ``loader_default`` defaults to
    :data:`tab_cli.registry.DEFAULT_THRESHOLD` (lazy-imported to keep
    this module from forcing the registry's import chain).
    """
    if overrides is None:
        overrides = load_overrides()

    if loader_default is None:
        # Lazy-import keeps this module callable from places that
        # haven't paid for grimoire's Postgres/Ollama import yet.
        from tab_cli.registry import DEFAULT_THRESHOLD

        loader_default = DEFAULT_THRESHOLD

    rows: list[EffectiveThreshold] = []
    for record in records:
        if record.name in overrides:
            rows.append(
                EffectiveThreshold(
                    name=record.name,
                    threshold=overrides[record.name],
                    source="override",
                )
            )
            continue

        # Frontmatter branch: dormant only because no SKILL.md
        # currently sets a non-default ``grimoire-threshold``. The
        # loader-side parser is already wired up, so the moment a
        # SKILL.md ships a non-default value this branch reads it as
        # ``frontmatter`` automatically — no change required here.
        if record.threshold != loader_default:
            rows.append(
                EffectiveThreshold(
                    name=record.name,
                    threshold=record.threshold,
                    source="frontmatter",
                )
            )
            continue

        rows.append(
            EffectiveThreshold(
                name=record.name,
                threshold=record.threshold,
                source="loader-default",
            )
        )

    return rows
