import json
import tempfile
import shutil
from pathlib import Path

from src.storage.metadata_store import FileMetadataStore


def test_file_metadata_store_write_and_read():
    tmp = tempfile.mkdtemp()
    try:
        base = Path(tmp) / "var"
        store = FileMetadataStore(base_path=str(base))

        frame_id = "frame-123"
        data = {"labels": ["cat", "dog"], "accuracy": 0.92}

        # save
        store.save_metadata(frame_id, data)

        # read back
        loaded = store.load_metadata(frame_id)
        assert loaded == data

        # file exists
        expected_path = base / "metadata" / "moondream" / f"{frame_id}.json"
        assert expected_path.exists()
        with expected_path.open("r", encoding="utf-8") as f:
            disk = json.load(f)
        assert disk == data
    finally:
        shutil.rmtree(tmp)
