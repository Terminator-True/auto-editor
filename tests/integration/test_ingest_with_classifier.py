import json
import time
from pathlib import Path

import pytest


def test_ingest_with_classifier_success(tmp_path, monkeypatch):
    # Arrange: create a file metadata store path
    store_dir = tmp_path / "var"
    # Create a fake classifier that returns metadata
    class FakeClassifier:
        def classify_frame(self, frame):
            return {"frame_id": frame["frame_id"], "top_label": "cat", "accuracy": 0.9}

    monkeypatch.setenv("MOONDREAM_METADATA_BASE", str(store_dir))

    # Act: import the ingest function and run
    from src.ingest.frames import ingest_frame
    from src.storage.metadata_store import FileMetadataStore

    store = FileMetadataStore(base_path=str(store_dir))
    frame = {"frame_id": "frame123", "data": "..."}

    result = ingest_frame(frame, classifier=FakeClassifier(), metadata_store=store, async_worker=False)

    # Assert: ingest returns True and metadata file exists and contains expected fields
    assert result is True
    p = store._path_for("frame123")
    assert p.exists()
    data = json.loads(p.read_text(encoding="utf-8"))
    assert data.get("top_label") == "cat"


def test_ingest_with_classifier_failure(tmp_path, monkeypatch):
    # Arrange: fake classifier that raises
    class FailingClassifier:
        def classify_frame(self, frame):
            raise RuntimeError("classification failed")

    from src.ingest.frames import ingest_frame
    from src.storage.metadata_store import FileMetadataStore

    store_dir = tmp_path / "var2"
    store = FileMetadataStore(base_path=str(store_dir))
    frame = {"frame_id": "frame456", "data": "..."}

    # Act: should not raise, ingest proceeds
    result = ingest_frame(frame, classifier=FailingClassifier(), metadata_store=store, async_worker=False)

    # Assert: ingest returns True and metadata file may not exist (but ingest must succeed)
    assert result is True
    p = store._path_for("frame456")
    # metadata should not exist because classification failed, but ingest still succeeded
    assert not p.exists()
