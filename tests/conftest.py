"""Shared pytest fixtures for offline testing against a fake Resolve API."""

from __future__ import annotations

from pathlib import Path

import pytest

from davinci_automation.jsonl_logger import JsonlLogger
from davinci_automation.resolve_client import ResolveClient
from tests.fake_resolve import FakeResolve, make_fake_project


@pytest.fixture
def fake_resolve():
    """Return a freshly constructed FakeResolve with one project and timeline."""
    return FakeResolve(
        projects={
            "TestProject": make_fake_project(
                "TestProject",
                timeline_name="Timeline 1",
                tracks={
                    1: ("video", [("Clip A", 0, 24), ("Clip B", 25, 60)]),
                    2: ("video", []),
                },
            )
        }
    )


@pytest.fixture
def client(fake_resolve, monkeypatch):
    """A ResolveClient whose connect() returns the FakeResolve instance."""
    client = ResolveClient(script_path=None, detect_version=True)
    monkeypatch.setattr(client, "connect", lambda: fake_resolve)
    return client


@pytest.fixture
def logger(tmp_path: Path) -> JsonlLogger:
    """A JsonlLogger writing to a temp file."""
    return JsonlLogger(tmp_path / "run.jsonl")
