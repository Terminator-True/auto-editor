import json
import os

from scripts import event_registry_cli as cli


def test_list_suggestions_empty(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    res = cli.list_suggestions("default", 5)
    assert res == []


def test_review_action_creates_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    out = cli.review_suggestion_action("sugg-1", True, merge_into="p1", dry_run=True)
    path = tmp_path / "event_registry" / "reviews" / "sugg-1.json"
    assert path.exists()
    data = json.loads(path.read_text())
    assert data["approve"] is True
