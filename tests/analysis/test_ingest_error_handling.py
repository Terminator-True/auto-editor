import pytest


def test_error_path_logs_and_continues(monkeypatch, tmp_path):
    # classifier that raises
    class BadClassifier:
        def classify_frame(self, frame):
            raise ValueError("boom")

    from src.ingest.frames import ingest_frame
    from src.storage.metadata_store import FileMetadataStore

    store = FileMetadataStore(base_path=str(tmp_path))
    frame = {"frame_id": "errframe", "data": "..."}

    # Should not raise
    assert ingest_frame(frame, classifier=BadClassifier(), metadata_store=store, async_worker=False) is True
