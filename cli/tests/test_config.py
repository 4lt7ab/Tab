"""Tests for `tab_cli.config.load_settings_from_config`."""

from __future__ import annotations

from pathlib import Path

import pytest

from tab_cli.config import load_settings_from_config


@pytest.fixture
def fake_xdg(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point `XDG_CONFIG_HOME` at a tmp dir and return the tab/ subdir."""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    tab_dir = tmp_path / "tab"
    tab_dir.mkdir()
    return tab_dir


def test_missing_file_returns_empty_dict(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    # No tab/config.toml created.
    result = load_settings_from_config()
    assert result == {}
    # Missing file is a silent no-op.
    captured = capsys.readouterr()
    assert captured.err == ""


def test_valid_full_config(fake_xdg: Path) -> None:
    (fake_xdg / "config.toml").write_text(
        "[settings]\n"
        "humor = 65\n"
        "directness = 80\n"
        "warmth = 70\n"
        "autonomy = 50\n"
        "verbosity = 35\n"
    )
    assert load_settings_from_config() == {
        "humor": 65,
        "directness": 80,
        "warmth": 70,
        "autonomy": 50,
        "verbosity": 35,
    }


def test_partial_config_returns_only_present_keys(fake_xdg: Path) -> None:
    (fake_xdg / "config.toml").write_text("[settings]\nhumor = 10\nwarmth = 0\n")
    assert load_settings_from_config() == {"humor": 10, "warmth": 0}


def test_boundary_values_are_accepted(fake_xdg: Path) -> None:
    (fake_xdg / "config.toml").write_text(
        "[settings]\nhumor = 0\ndirectness = 100\n"
    )
    assert load_settings_from_config() == {"humor": 0, "directness": 100}


def test_malformed_toml_warns_and_returns_empty(
    fake_xdg: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (fake_xdg / "config.toml").write_text("[settings\nhumor = 65\n")
    result = load_settings_from_config()
    assert result == {}
    captured = capsys.readouterr()
    assert "tab:" in captured.err
    assert "malformed" in captured.err
    assert "config.toml" in captured.err


def test_out_of_range_drops_key_and_warns(
    fake_xdg: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (fake_xdg / "config.toml").write_text(
        "[settings]\nhumor = 150\ndirectness = 80\n"
    )
    result = load_settings_from_config()
    assert result == {"directness": 80}
    captured = capsys.readouterr()
    assert "tab:" in captured.err
    assert "humor" in captured.err
    assert "150" in captured.err


def test_negative_value_drops_key_and_warns(
    fake_xdg: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (fake_xdg / "config.toml").write_text(
        "[settings]\nhumor = -1\nwarmth = 70\n"
    )
    result = load_settings_from_config()
    assert result == {"warmth": 70}
    assert "humor" in capsys.readouterr().err


def test_wrong_type_drops_key_and_warns(
    fake_xdg: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (fake_xdg / "config.toml").write_text(
        '[settings]\nhumor = "loud"\nverbosity = 25\n'
    )
    result = load_settings_from_config()
    assert result == {"verbosity": 25}
    captured = capsys.readouterr()
    assert "humor" in captured.err


def test_bool_is_rejected(
    fake_xdg: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # bool is an int subclass in Python; make sure we don't silently
    # coerce `humor = true` to 1.
    (fake_xdg / "config.toml").write_text(
        "[settings]\nhumor = true\nautonomy = 40\n"
    )
    result = load_settings_from_config()
    assert result == {"autonomy": 40}
    assert "humor" in capsys.readouterr().err


def test_unknown_keys_are_ignored_silently(
    fake_xdg: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (fake_xdg / "config.toml").write_text(
        "[settings]\nhumor = 65\nmysterious = 999\n"
    )
    assert load_settings_from_config() == {"humor": 65}
    # Unknown keys don't warn — they may be from a future version.
    assert capsys.readouterr().err == ""


def test_missing_settings_table(fake_xdg: Path) -> None:
    (fake_xdg / "config.toml").write_text("[other]\nfoo = 1\n")
    assert load_settings_from_config() == {}


def test_xdg_config_home_redirects_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    elsewhere = tmp_path / "elsewhere"
    (elsewhere / "tab").mkdir(parents=True)
    (elsewhere / "tab" / "config.toml").write_text("[settings]\nhumor = 42\n")

    # The default ~/.config path should NOT be used.
    monkeypatch.setenv("XDG_CONFIG_HOME", str(elsewhere))
    assert load_settings_from_config() == {"humor": 42}


def test_xdg_unset_falls_back_to_home_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    fake_home = tmp_path / "home"
    (fake_home / ".config" / "tab").mkdir(parents=True)
    (fake_home / ".config" / "tab" / "config.toml").write_text(
        "[settings]\nautonomy = 55\n"
    )
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: fake_home))
    assert load_settings_from_config() == {"autonomy": 55}
