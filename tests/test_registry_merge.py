import json
import os

from event_categorization import registry_merge


def test_merge_dry_run(tmp_path, monkeypatch):
    base = tmp_path
    game = "testgame"
    er = base / "event_registry" / game
    er.mkdir(parents=True)
    registry_path = base / "event_registry" / game / "registry.json"
    registry = {"p1": {"name": "primary"}, "d1": {"name": "dup"}}
    registry_path.write_text(json.dumps(registry))

    # monkeypatch os path references to use tmp_path
    monkeypatch.chdir(base)

    res = registry_merge.merge_events(game, "p1", ["d1"], dry_run=True)
    assert res["dry_run"] is True
    assert any(op.get("dup") == "d1" for op in res["ops"])
