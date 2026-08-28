"""Tests for CLI orchestration: exit codes and JSONL events per spec scenario."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from davinci_automation import cli
from davinci_automation.resolve_client import (
    NoActiveTimeline,
    NoOpenProject,
    ResolveNotRunning,
    ResolveScriptNotFound,
)
from tests.fake_resolve import FakeProject, FakeResolve, make_fake_project


class FakeClient:
    """Drops-in for ResolveClient so the CLI runs against a FakeResolve."""

    def __init__(self, fake_resolve, fail=None, script_path=None, detect_version=True):
        self._resolve = fake_resolve
        self.fail = fail
        self.detect_version = detect_version

    def connect(self):
        if self.fail == "connect":
            raise ResolveNotRunning("not running")
        if self.fail == "script":
            raise ResolveScriptNotFound("no module")
        return self._resolve

    def get_version(self):
        return self._resolve.GetVersionString()

    def active_project(self):
        if self.fail == "project":
            raise NoOpenProject("no project")
        project = self._resolve.GetProjectManager().GetCurrentProject()
        if project is None:
            raise NoOpenProject("no project")
        return project

    def active_timeline(self):
        if self.fail == "timeline":
            raise NoActiveTimeline("no timeline")
        return self.active_project().GetCurrentTimeline()


@pytest.fixture
def cfg_path(tmp_path: Path) -> Path:
    log_path = tmp_path / "run.jsonl"
    path = tmp_path / "config.yaml"
    path.write_text(f"resolve:\n  script_path: null\n  detect_version: true\n"
                    f"log:\n  path: {log_path}\n  level: info\n", encoding="utf-8")
    return path


@pytest.fixture
def events(cfg_path: Path):
    log_path = Path(cfg_path.parent / "run.jsonl")

    def _events():
        if not log_path.is_file():
            return []
        return [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]

    return _events


def _patch_client(monkeypatch, fake_resolve, fail=None) -> None:
    monkeypatch.setattr(
        cli,
        "ResolveClient",
        lambda script_path=None, detect_version=True: FakeClient(
            fake_resolve, fail=fail, script_path=script_path, detect_version=detect_version
        ),
    )


def test_success_returns_0_and_logs_session(monkeypatch, cfg_path, fake_resolve, events) -> None:
    _patch_client(monkeypatch, fake_resolve)

    assert cli.main(["--config", str(cfg_path)]) == 0

    names = [e["event"] for e in events()]
    assert names == [
        "connection",
        "version",
        "project",
        "timeline",
        "track",
        "clip",
        "clip",
        "track",
    ]


def test_empty_timeline_returns_0(monkeypatch, cfg_path, events) -> None:
    resolve = FakeResolve(projects={"P": make_fake_project("P", timeline_name="T1", tracks={})})
    _patch_client(monkeypatch, resolve)

    assert cli.main(["--config", str(cfg_path)]) == 0
    assert events()[-1]["event"] == "empty_timeline"


def test_connect_error_returns_1(monkeypatch, cfg_path, events) -> None:
    resolve = FakeResolve(projects={})
    _patch_client(monkeypatch, resolve, fail="connect")

    assert cli.main(["--config", str(cfg_path)]) == 1
    assert events()[-1]["event"] == "connect_error"


def test_project_error_returns_1(monkeypatch, cfg_path, events) -> None:
    resolve = FakeResolve(projects={})
    _patch_client(monkeypatch, resolve, fail="project")

    assert cli.main(["--config", str(cfg_path)]) == 1
    assert events()[-1]["event"] == "project_error"


def test_timeline_error_returns_1(monkeypatch, cfg_path, events) -> None:
    project = FakeProject(name="P", timeline=None, timeline_name=None)
    resolve = FakeResolve(projects={"P": project})
    _patch_client(monkeypatch, resolve, fail="timeline")

    assert cli.main(["--config", str(cfg_path)]) == 1
    assert events()[-1]["event"] == "timeline_error"


def test_script_not_found_returns_1(monkeypatch, cfg_path, events) -> None:
    resolve = FakeResolve(projects={})
    _patch_client(monkeypatch, resolve, fail="script")

    assert cli.main(["--config", str(cfg_path)]) == 1
    assert events()[-1]["event"] == "script_not_found"


def test_missing_config_returns_1(tmp_path: Path) -> None:
    assert cli.main(["--config", str(tmp_path / "absent.yaml")]) == 1


def test_detect_version_false_skips_version_event(monkeypatch, tmp_path: Path, fake_resolve) -> None:
    log_path = tmp_path / "run.jsonl"
    cfg = tmp_path / "config.yaml"
    cfg.write_text(f"resolve:\n  script_path: null\n  detect_version: false\n"
                   f"log:\n  path: {log_path}\n  level: info\n", encoding="utf-8")
    _patch_client(monkeypatch, fake_resolve)

    assert cli.main(["--config", str(cfg)]) == 0
    records = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]
    assert all(r["event"] != "version" for r in records)