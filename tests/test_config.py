"""Tests for config loading and validation."""

from __future__ import annotations

from pathlib import Path

import pytest

from davinci_automation.config import ConfigError, load_config


def _write(path: Path, content: str) -> Path:
    path.write_text(content, encoding="utf-8")
    return path


def test_loads_valid_config(tmp_path: Path) -> None:
    cfg = _write(
        tmp_path / "config.yaml",
        "resolve:\n  script_path: /opt/resolve/Developer/Scripting/Modules\n"
        "  detect_version: true\nlog:\n  path: logs/run.jsonl\n  level: info\n",
    )
    config = load_config(cfg)
    assert config.resolve.script_path == "/opt/resolve/Developer/Scripting/Modules"
    assert config.resolve.detect_version is True
    assert config.log.path == Path("logs/run.jsonl")
    assert config.log.level == "info"


def test_defaults_when_sections_omitted(tmp_path: Path) -> None:
    cfg = _write(tmp_path / "config.yaml", "log:\n  path: logs/run.jsonl\n")
    config = load_config(cfg)
    assert config.resolve.script_path is None
    assert config.resolve.detect_version is True
    assert config.log.level == "info"


def test_missing_config_file_raises(tmp_path: Path) -> None:
    with pytest.raises(ConfigError):
        load_config(tmp_path / "does_not_exist.yaml")


def test_invalid_yaml_raises(tmp_path: Path) -> None:
    cfg = _write(tmp_path / "config.yaml", "resolve: [unclosed\n  : : :\n")
    with pytest.raises(ConfigError):
        load_config(cfg)


def test_empty_config_raises(tmp_path: Path) -> None:
    cfg = _write(tmp_path / "config.yaml", "")
    with pytest.raises(ConfigError):
        load_config(cfg)


def test_invalid_script_path_type_raises(tmp_path: Path) -> None:
    cfg = _write(tmp_path / "config.yaml", "resolve:\n  script_path: 123\n")
    with pytest.raises(ConfigError):
        load_config(cfg)


def test_invalid_detect_version_type_raises(tmp_path: Path) -> None:
    cfg = _write(tmp_path / "config.yaml", "resolve:\n  detect_version: 'yes'\n")
    with pytest.raises(ConfigError):
        load_config(cfg)


def test_invalid_log_path_type_raises(tmp_path: Path) -> None:
    cfg = _write(tmp_path / "config.yaml", "log:\n  path: 42\n")
    with pytest.raises(ConfigError):
        load_config(cfg)