"""Read personality settings from `~/.config/tab/config.toml`.

The flag-merger lives in another ticket; this module just exposes
`load_settings_from_config()`. It returns a dict of the keys it found
that passed validation. Missing file is fine, malformed file warns and
falls through, out-of-range values warn and drop just that key.
"""

from __future__ import annotations

import os
import sys
import tomllib
from pathlib import Path

# Personality settings the Tab agent accepts. Keys outside this set in the
# config file are ignored silently — they may belong to a future setting
# or a typo we don't want to be noisy about.
_VALID_KEYS = ("humor", "directness", "warmth", "autonomy", "verbosity")


def _config_path() -> Path:
    """Resolve the config path, honoring `XDG_CONFIG_HOME`."""
    xdg = os.environ.get("XDG_CONFIG_HOME")
    base = Path(xdg) if xdg else Path.home() / ".config"
    return base / "tab" / "config.toml"


def _warn(message: str) -> None:
    print(f"tab: {message}", file=sys.stderr)


def load_settings_from_config() -> dict[str, int]:
    """Load the `[settings]` table from the user's tab config.

    Returns a dict containing only keys that parsed and validated as
    ints in [0, 100]. Missing file → empty dict, no warning. Malformed
    TOML → empty dict with one stderr warning. Per-key validation
    failures emit one stderr warning each and drop only the offending
    key.
    """
    path = _config_path()

    try:
        raw = path.read_bytes()
    except FileNotFoundError:
        return {}
    except OSError as exc:
        _warn(f"could not read {path}: {exc}")
        return {}

    try:
        data = tomllib.loads(raw.decode("utf-8"))
    except (tomllib.TOMLDecodeError, UnicodeDecodeError) as exc:
        _warn(f"ignoring malformed config {path}: {exc}")
        return {}

    settings = data.get("settings")
    if not isinstance(settings, dict):
        return {}

    result: dict[str, int] = {}
    for key in _VALID_KEYS:
        if key not in settings:
            continue
        value = settings[key]
        # bool is a subclass of int — reject it explicitly so
        # `humor = true` doesn't sneak through as 1.
        if not isinstance(value, int) or isinstance(value, bool):
            _warn(
                f"ignoring invalid setting '{key}={value!r}' in {path} "
                "(must be int 0-100)"
            )
            continue
        if not 0 <= value <= 100:
            _warn(
                f"ignoring invalid setting '{key}={value}' in {path} "
                "(must be int 0-100)"
            )
            continue
        result[key] = value

    return result
