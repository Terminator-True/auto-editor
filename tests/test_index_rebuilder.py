import time

from event_categorization.index_rebuilder import IndexRebuilder


def test_rebuilder_queue(tmp_path, monkeypatch):
    # run in tmp dir
    monkeypatch.chdir(tmp_path)
    reb = IndexRebuilder(game="g1")
    reb.request_rebuild("test")
    # allow background thread to process
    time.sleep(0.5)
    base = tmp_path / "event_registry" / "index" / "g1"
    assert (base / "rebuilt.json").exists()
    reb.stop()
