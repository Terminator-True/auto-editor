"""Tests for CLI orchestration: exit codes and JSONL events per spec scenario."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from davinci_automation import cli
from davinci_automation.ollama_client import (
    OllamaConnectionError,
    OllamaModelNotFoundError,
    OllamaResponseError,
    OllamaResult,
    OllamaTemplateError,
    OllamaTimeoutError,
)
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


# ------------------------------------------------------------ --probe-ollama

class FakeOllamaClient:
    """Drops-in for OllamaClient so the CLI probe runs offline."""

    def __init__(self, result=None, error=None, **kwargs):
        self.result = result
        self.error = error
        self.kwargs = kwargs

    def probe(self):
        if self.error is not None:
            raise self.error
        return self.result


@pytest.fixture
def ollama_cfg_path(tmp_path: Path) -> Path:
    log_path = tmp_path / "run.jsonl"
    path = tmp_path / "config.yaml"
    path.write_text(
        f"log:\n  path: {log_path}\n  level: info\n"
        f"ollama:\n  endpoint: http://localhost:11434\n  model: qwen2.5:14b\n"
        f"  temperature: 0.2\n  timeout: 5.0\n  prompt_template: {tmp_path}/system.md\n",
        encoding="utf-8",
    )
    return path


def _patch_ollama(monkeypatch, result=None, error=None) -> None:
    monkeypatch.setattr(
        cli,
        "OllamaClient",
        lambda **kwargs: FakeOllamaClient(result=result, error=error, **kwargs),
    )


def test_probe_ollama_success_returns_0(monkeypatch, ollama_cfg_path, events) -> None:
    _patch_ollama(
        monkeypatch,
        result=OllamaResult(
            ok=True,
            response="ok",
            latency_s=0.012,
            ollama={"total_duration_ns": 1500000000, "eval_count": 3},
        ),
    )

    assert cli.main(["--probe-ollama", "--config", str(ollama_cfg_path)]) == 0

    names = [e["event"] for e in events()]
    assert names == ["probe_start", "probe_success"]
    success = events()[1]["result"]
    assert success["response"] == "ok"
    assert success["latency_s"] == 0.012
    assert success["total_duration_ns"] == 1500000000


def test_probe_ollama_connection_error_returns_1(monkeypatch, ollama_cfg_path, events) -> None:
    _patch_ollama(monkeypatch, error=OllamaConnectionError("cannot reach Ollama at ..."))

    assert cli.main(["--probe-ollama", "--config", str(ollama_cfg_path)]) == 1
    assert events()[-1]["event"] == "probe_error"
    assert "cannot reach" in events()[-1]["result"]["message"]


def test_probe_ollama_model_not_found_returns_1(monkeypatch, ollama_cfg_path, events) -> None:
    _patch_ollama(monkeypatch, error=OllamaModelNotFoundError("model not found"))

    assert cli.main(["--probe-ollama", "--config", str(ollama_cfg_path)]) == 1
    assert events()[-1]["event"] == "probe_error"


def test_probe_ollama_timeout_returns_1(monkeypatch, ollama_cfg_path, events) -> None:
    _patch_ollama(monkeypatch, error=OllamaTimeoutError("timed out"))

    assert cli.main(["--probe-ollama", "--config", str(ollama_cfg_path)]) == 1
    assert events()[-1]["event"] == "probe_error"


def test_probe_ollama_template_error_returns_1(monkeypatch, ollama_cfg_path, events) -> None:
    _patch_ollama(monkeypatch, error=OllamaTemplateError("cannot read template"))

    assert cli.main(["--probe-ollama", "--config", str(ollama_cfg_path)]) == 1
    assert events()[-1]["event"] == "probe_error"


def test_probe_ollama_response_error_returns_1(monkeypatch, ollama_cfg_path, events) -> None:
    _patch_ollama(monkeypatch, error=OllamaResponseError("no usable response"))

    assert cli.main(["--probe-ollama", "--config", str(ollama_cfg_path)]) == 1
    assert events()[-1]["event"] == "probe_error"