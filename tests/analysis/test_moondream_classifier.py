import tempfile
import shutil
from pathlib import Path

from src.analysis.moondream_classifier import MoondreamClassifier
from src.storage.metadata_store import FileMetadataStore


def test_classifier_maps_and_persists(monkeypatch):
    tmp = tempfile.mkdtemp()
    try:
        base = Path(tmp) / "var"
        store = FileMetadataStore(base_path=str(base))

        # fake ollama client
        class FakeClient:
            def get_labels(self, frames, model, top_n):
                return [{"label": "cat", "confidence": 0.8}, {"label": "dog", "confidence": 0.2}]

        clf = MoondreamClassifier(ollama_client=FakeClient(), metadata_store=store, taxonomy_map={"cat": "animal"})

        frame = {"frame_id": "f1", "data": "..."}
        res = clf.classify_frame(frame)

        # classifier maps 'cat' -> 'animal' per taxonomy_map
        assert res["top_label"] == "animal"
        assert res["accuracy"] == 0.8

        # persisted (should reflect mapped label)
        loaded = store.load_metadata("f1")
        assert loaded["top_label"] == "animal"
    finally:
        shutil.rmtree(tmp)
