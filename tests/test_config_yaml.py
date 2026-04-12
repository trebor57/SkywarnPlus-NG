"""Smoke test: load packaged default YAML."""

from pathlib import Path

import pytest

from skywarnplus_ng.core.config import AppConfig, ConfigError


def test_load_default_yaml():
    root = Path(__file__).resolve().parents[1]
    path = root / "config" / "default.yaml"
    cfg = AppConfig.from_yaml(path)
    assert cfg.enabled is True
    assert cfg.poll_interval >= 1
    assert len(cfg.counties) >= 1


def test_from_yaml_missing_file_returns_defaults(tmp_path):
    missing = tmp_path / "nope.yaml"
    cfg = AppConfig.from_yaml(missing)
    assert isinstance(cfg, AppConfig)


def test_from_yaml_rejects_non_mapping(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text("- not a mapping\n")
    with pytest.raises(ConfigError):
        AppConfig.from_yaml(bad)
