import json
from pathlib import Path
from typing import Protocol, Any, Dict


class MetadataStore(Protocol):
    def save_metadata(self, frame_id: str, metadata: Dict[str, Any]) -> None:
        ...

    def load_metadata(self, frame_id: str) -> Dict[str, Any]:
        ...


class FileMetadataStore:
    def __init__(self, base_path: str = "var"):
        self.base = Path(base_path)

    def _path_for(self, frame_id: str) -> Path:
        d = self.base / "metadata" / "moondream"
        d.mkdir(parents=True, exist_ok=True)
        return d / f"{frame_id}.json"

    def save_metadata(self, frame_id: str, metadata: Dict[str, Any]) -> None:
        p = self._path_for(frame_id)
        with p.open("w", encoding="utf-8") as f:
            json.dump(metadata, f)

    def load_metadata(self, frame_id: str) -> Dict[str, Any]:
        p = self._path_for(frame_id)
        if not p.exists():
            raise FileNotFoundError(str(p))
        with p.open("r", encoding="utf-8") as f:
            return json.load(f)
