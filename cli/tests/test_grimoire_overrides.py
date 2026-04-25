"""Tests for :mod:`tab_cli.grimoire_overrides`.

Covers the persisted store (load/save/set/reset), validation, and the
``effective_thresholds`` layering function. The persistence path is
exercised against a temporary directory; ``XDG_CONFIG_HOME`` is the
seam.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tab_cli.grimoire_overrides import (
    EffectiveThreshold,
    OverrideError,
    effective_thresholds,
    load_overrides,
    overrides_path,
    reset_override,
    save_overrides,
    set_override,
)
from tab_cli.registry import DEFAULT_THRESHOLD, SkillRecord


@pytest.fixture
def fake_xdg(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point ``XDG_CONFIG_HOME`` at a tmp dir; return the resolved tab/ subdir."""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    return tmp_path / "tab"


# ----------------------------------------------------- path resolution


def test_overrides_path_honors_xdg_config_home(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    assert overrides_path() == tmp_path / "tab" / "grimoire-overrides.json"


def test_overrides_path_falls_back_to_home_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    assert overrides_path() == tmp_path / ".config" / "tab" / "grimoire-overrides.json"


# ----------------------------------------------------------- load


def test_load_missing_file_returns_empty_dict(fake_xdg: Path) -> None:
    # No file created. Should be a clean empty dict.
    assert load_overrides() == {}


def test_load_round_trips_a_saved_file(fake_xdg: Path) -> None:
    save_overrides({"draw-dino": 0.45, "teach": 0.7})
    assert load_overrides() == {"draw-dino": 0.45, "teach": 0.7}


def test_load_rejects_malformed_json(fake_xdg: Path) -> None:
    fake_xdg.mkdir()
    (fake_xdg / "grimoire-overrides.json").write_text("not json", encoding="utf-8")
    with pytest.raises(OverrideError, match="malformed"):
        load_overrides()


def test_load_rejects_non_object_top_level(fake_xdg: Path) -> None:
    fake_xdg.mkdir()
    (fake_xdg / "grimoire-overrides.json").write_text("[]", encoding="utf-8")
    with pytest.raises(OverrideError, match="JSON object"):
        load_overrides()


def test_load_rejects_thresholds_not_object(fake_xdg: Path) -> None:
    fake_xdg.mkdir()
    (fake_xdg / "grimoire-overrides.json").write_text(
        json.dumps({"version": 1, "thresholds": []}), encoding="utf-8"
    )
    with pytest.raises(OverrideError, match="thresholds"):
        load_overrides()


def test_load_rejects_out_of_range_threshold(fake_xdg: Path) -> None:
    fake_xdg.mkdir()
    (fake_xdg / "grimoire-overrides.json").write_text(
        json.dumps({"version": 1, "thresholds": {"draw-dino": 1.5}}),
        encoding="utf-8",
    )
    with pytest.raises(OverrideError, match=r"\[0.0, 1.0\]"):
        load_overrides()


def test_load_rejects_negative_threshold(fake_xdg: Path) -> None:
    fake_xdg.mkdir()
    (fake_xdg / "grimoire-overrides.json").write_text(
        json.dumps({"version": 1, "thresholds": {"draw-dino": -0.1}}),
        encoding="utf-8",
    )
    with pytest.raises(OverrideError):
        load_overrides()


def test_load_rejects_non_numeric_threshold(fake_xdg: Path) -> None:
    fake_xdg.mkdir()
    (fake_xdg / "grimoire-overrides.json").write_text(
        json.dumps({"version": 1, "thresholds": {"draw-dino": "hot"}}),
        encoding="utf-8",
    )
    with pytest.raises(OverrideError, match="number"):
        load_overrides()


def test_load_rejects_bool_threshold(fake_xdg: Path) -> None:
    fake_xdg.mkdir()
    # bool is a subclass of int — make sure the validator catches it.
    (fake_xdg / "grimoire-overrides.json").write_text(
        json.dumps({"version": 1, "thresholds": {"draw-dino": True}}),
        encoding="utf-8",
    )
    with pytest.raises(OverrideError, match="number"):
        load_overrides()


def test_load_accepts_int_threshold_at_boundaries(fake_xdg: Path) -> None:
    fake_xdg.mkdir()
    (fake_xdg / "grimoire-overrides.json").write_text(
        json.dumps({"version": 1, "thresholds": {"a": 0, "b": 1}}),
        encoding="utf-8",
    )
    assert load_overrides() == {"a": 0.0, "b": 1.0}


# ------------------------------------------------------------- save


def test_save_creates_parent_directory(fake_xdg: Path) -> None:
    # fake_xdg exists as a path but isn't materialized yet.
    assert not fake_xdg.exists()
    save_overrides({"draw-dino": 0.45})
    assert fake_xdg.is_dir()
    assert (fake_xdg / "grimoire-overrides.json").is_file()


def test_save_writes_sorted_pretty_json(fake_xdg: Path) -> None:
    save_overrides({"teach": 0.7, "draw-dino": 0.45})
    raw = (fake_xdg / "grimoire-overrides.json").read_text(encoding="utf-8")
    decoded = json.loads(raw)
    assert decoded == {
        "version": 1,
        "thresholds": {"draw-dino": 0.45, "teach": 0.7},
    }
    # Sorted keys produce the same byte sequence on every save —
    # a hand-edit-then-CLI-write round-trip stays stable in diff.
    keys_in_file_order = list(decoded["thresholds"].keys())
    assert keys_in_file_order == sorted(keys_in_file_order)


# ------------------------------------------------------- set / reset


def test_set_round_trips_through_load(fake_xdg: Path) -> None:
    set_override("draw-dino", 0.45)
    assert load_overrides() == {"draw-dino": 0.45}


def test_set_then_set_replaces_previous(fake_xdg: Path) -> None:
    set_override("draw-dino", 0.45)
    set_override("draw-dino", 0.55)
    assert load_overrides() == {"draw-dino": 0.55}


def test_set_then_set_other_skill_keeps_both(fake_xdg: Path) -> None:
    set_override("draw-dino", 0.45)
    set_override("teach", 0.7)
    assert load_overrides() == {"draw-dino": 0.45, "teach": 0.7}


def test_set_rejects_out_of_range_threshold(fake_xdg: Path) -> None:
    with pytest.raises(OverrideError, match=r"\[0.0, 1.0\]"):
        set_override("draw-dino", 1.5)


def test_set_rejects_negative_threshold(fake_xdg: Path) -> None:
    with pytest.raises(OverrideError):
        set_override("draw-dino", -0.1)


def test_set_rejects_empty_skill_name(fake_xdg: Path) -> None:
    with pytest.raises(OverrideError, match="non-empty"):
        set_override("   ", 0.5)


def test_set_rejects_bool_threshold(fake_xdg: Path) -> None:
    with pytest.raises(OverrideError, match="number"):
        set_override("draw-dino", True)  # type: ignore[arg-type]


def test_set_accepts_boundary_values(fake_xdg: Path) -> None:
    set_override("a", 0.0)
    set_override("b", 1.0)
    assert load_overrides() == {"a": 0.0, "b": 1.0}


def test_reset_returns_true_when_override_existed(fake_xdg: Path) -> None:
    set_override("draw-dino", 0.45)
    assert reset_override("draw-dino") is True
    assert load_overrides() == {}


def test_reset_returns_false_when_no_override_existed(fake_xdg: Path) -> None:
    # Idempotent — the CLI uses this to decide what message to print.
    assert reset_override("draw-dino") is False
    assert load_overrides() == {}


def test_reset_keeps_other_overrides(fake_xdg: Path) -> None:
    set_override("draw-dino", 0.45)
    set_override("teach", 0.7)
    assert reset_override("draw-dino") is True
    assert load_overrides() == {"teach": 0.7}


def test_reset_rejects_empty_skill_name(fake_xdg: Path) -> None:
    with pytest.raises(OverrideError, match="non-empty"):
        reset_override("")


# ----------------------------------------------------- effective_thresholds


def _make_record(name: str, threshold: float = DEFAULT_THRESHOLD) -> SkillRecord:
    return SkillRecord(
        name=name,
        description=f"Description for {name}",
        threshold=threshold,
        path=Path("/tmp") / name / "SKILL.md",
    )


def test_effective_thresholds_reports_loader_default_for_record_at_default(
    fake_xdg: Path,
) -> None:
    records = [_make_record("draw-dino")]
    rows = effective_thresholds(records, overrides={})
    assert rows == [
        EffectiveThreshold(
            name="draw-dino",
            threshold=DEFAULT_THRESHOLD,
            source="loader-default",
        )
    ]


def test_effective_thresholds_reports_override_when_set(fake_xdg: Path) -> None:
    records = [_make_record("draw-dino")]
    rows = effective_thresholds(records, overrides={"draw-dino": 0.45})
    assert rows == [
        EffectiveThreshold(
            name="draw-dino",
            threshold=0.45,
            source="override",
        )
    ]


def test_effective_thresholds_reports_frontmatter_when_record_diverges(
    fake_xdg: Path,
) -> None:
    """A record carrying a non-default threshold reads as 'frontmatter'.

    This branch is dormant in v0 (the loader hasn't learned to read
    frontmatter ``grimoire-threshold`` yet) but the layering must
    handle it correctly today so the field lights up cleanly when the
    loader-side ticket lands.
    """
    records = [_make_record("draw-dino", threshold=0.42)]
    rows = effective_thresholds(records, overrides={})
    assert rows == [
        EffectiveThreshold(
            name="draw-dino",
            threshold=0.42,
            source="frontmatter",
        )
    ]


def test_effective_thresholds_override_wins_over_frontmatter(fake_xdg: Path) -> None:
    """Even if the record had a frontmatter value, the user override wins."""
    records = [_make_record("draw-dino", threshold=0.42)]
    rows = effective_thresholds(records, overrides={"draw-dino": 0.55})
    assert rows == [
        EffectiveThreshold(
            name="draw-dino",
            threshold=0.55,
            source="override",
        )
    ]


def test_effective_thresholds_preserves_record_order(fake_xdg: Path) -> None:
    records = [
        _make_record("draw-dino"),
        _make_record("listen"),
        _make_record("teach"),
        _make_record("think"),
    ]
    rows = effective_thresholds(records, overrides={})
    assert [row.name for row in rows] == ["draw-dino", "listen", "teach", "think"]


def test_effective_thresholds_pulls_overrides_from_disk_when_omitted(
    fake_xdg: Path,
) -> None:
    set_override("draw-dino", 0.45)
    records = [_make_record("draw-dino"), _make_record("teach")]
    rows = effective_thresholds(records)
    sources = {row.name: row.source for row in rows}
    thresholds = {row.name: row.threshold for row in rows}
    assert sources == {"draw-dino": "override", "teach": "loader-default"}
    assert thresholds == {"draw-dino": 0.45, "teach": DEFAULT_THRESHOLD}
