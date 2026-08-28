"""Tests for ResolveClient script loading, connection, and reads."""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest

from davinci_automation import resolve_client as rc
from davinci_automation.resolve_client import (
    NoActiveTimeline,
    NoOpenProject,
    ResolveClient,
    ResolveNotRunning,
    ResolveScriptNotFound,
)
from tests.fake_resolve import FakeProject, FakeResolve, make_fake_project


class FakeScriptModule:
    """Mimics ``DaVinciResolveScript`` enough for connect()."""

    def __init__(self, resolve=None, raise_on_scriptapp=False):
        self.resolve = resolve
        self.raise_on_scriptapp = raise_on_scriptapp

    def scriptapp(self, name):
        if self.raise_on_scriptapp:
            raise RuntimeError("boom")
        return self.resolve


def _client_with_module(resolve=None, raise_on_scriptapp=False) -> ResolveClient:
    client = ResolveClient()
    client._script_module = FakeScriptModule(resolve, raise_on_scriptapp=raise_on_scriptapp)
    return client


# -- script loading ---------------------------------------------------------


def test_load_script_uses_configured_path(monkeypatch, tmp_path: Path) -> None:
    script_dir = tmp_path / "modules"
    script_dir.mkdir()
    sentinel = object()
    monkeypatch.setattr(
        rc.importlib,
        "import_module",
        lambda name: sentinel if name == "DaVinciResolveScript" else importlib.import_module(name),
    )

    client = ResolveClient(script_path=str(script_dir))
    assert client.load_script() is sentinel
    assert str(script_dir) in rc.sys.path


def test_load_script_missing_configured_path_raises(tmp_path: Path) -> None:
    client = ResolveClient(script_path=str(tmp_path / "nope"))
    with pytest.raises(ResolveScriptNotFound):
        client.load_script()


def test_load_script_default_import(monkeypatch) -> None:
    sentinel = object()
    monkeypatch.setattr(
        rc.importlib,
        "import_module",
        lambda name: sentinel if name == "DaVinciResolveScript" else importlib.import_module(name),
    )
    client = ResolveClient(script_path=None)
    assert client.load_script() is sentinel


def test_load_script_probes_platform_defaults(monkeypatch, tmp_path: Path) -> None:
    module_dir = tmp_path / "modules"
    module_dir.mkdir()
    monkeypatch.setattr(rc, "PLATFORM_MODULE_DIRS", [module_dir])
    sentinel = object()

    def fake_import(name):
        if name != "DaVinciResolveScript":
            return importlib.import_module(name)
        if str(module_dir) not in rc.sys.path:
            raise ModuleNotFoundError(f"No module named {name}")
        return sentinel

    monkeypatch.setattr(rc.importlib, "import_module", fake_import)
    client = ResolveClient(script_path=None)
    assert client.load_script() is sentinel


def test_load_script_not_found_raises(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(rc, "PLATFORM_MODULE_DIRS", [tmp_path / "empty"])
    monkeypatch.setattr(
        rc.importlib,
        "import_module",
        lambda name: (_ for _ in ()).throw(ModuleNotFoundError(name)),
    )
    client = ResolveClient(script_path=None)
    with pytest.raises(ResolveScriptNotFound):
        client.load_script()


# -- connection -------------------------------------------------------------


def test_connect_returns_resolve(fake_resolve) -> None:
    client = _client_with_module(fake_resolve)
    assert client.connect() is fake_resolve


def test_connect_none_raises_not_running() -> None:
    client = _client_with_module(None)
    with pytest.raises(ResolveNotRunning):
        client.connect()


def test_connect_scriptapp_raise_raises_not_running() -> None:
    client = _client_with_module(None, raise_on_scriptapp=True)
    with pytest.raises(ResolveNotRunning):
        client.connect()


# -- reads ------------------------------------------------------------------


def test_get_version_returns_string(fake_resolve) -> None:
    client = _client_with_module(fake_resolve)
    client.connect()
    assert client.get_version() == fake_resolve.GetVersionString()


def test_get_version_returns_none_on_failure() -> None:
    class BadResolve:
        def GetVersionString(self):
            raise RuntimeError("nope")

    client = _client_with_module(BadResolve())
    client.connect()
    assert client.get_version() is None


def test_active_project_returns_project() -> None:
    resolve = FakeResolve(projects={"P": make_fake_project("P", timeline_name="T1", tracks={})})
    client = _client_with_module(resolve)
    client.connect()
    assert client.active_project().GetName() == "P"


def test_active_project_none_raises() -> None:
    resolve = FakeResolve(projects={})
    client = _client_with_module(resolve)
    client.connect()
    with pytest.raises(NoOpenProject):
        client.active_project()


def test_active_timeline_returns_timeline() -> None:
    resolve = FakeResolve(projects={"P": make_fake_project("P", timeline_name="T1", tracks={})})
    client = _client_with_module(resolve)
    client.connect()
    assert client.active_timeline().GetName() == "T1"


def test_active_timeline_none_raises() -> None:
    project = FakeProject(name="P", timeline=None, timeline_name=None)
    resolve = FakeResolve(projects={"P": project})
    client = _client_with_module(resolve)
    client.connect()
    with pytest.raises(NoActiveTimeline):
        client.active_timeline()