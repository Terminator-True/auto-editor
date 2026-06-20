from typing import Any, Dict


class MoondreamClassifier:
    def __init__(self, ollama_client, metadata_store, taxonomy_map: Dict[str, str] = None):
        self.client = ollama_client
        self.store = metadata_store
        self.taxonomy_map = taxonomy_map or {}

    def classify_frame(self, frame: Dict[str, Any]) -> Dict[str, Any]:
        frame_id = frame.get("frame_id")
        frames = [frame]
        labels = self.client.get_labels(frames=frames, model="moondream-v1", top_n=3)

        if not labels:
            result = {"frame_id": frame_id, "top_label": None, "accuracy": 0.0, "labels": []}
            self.store.save_metadata(frame_id, result)
            return result

        top = labels[0]
        mapped = self.taxonomy_map.get(top["label"], top["label"]) if top["label"] else None

        result = {
            "frame_id": frame_id,
            "top_label": mapped,
            "accuracy": top.get("confidence", 0.0),
            "labels": labels,
        }

        self.store.save_metadata(frame_id, result)
        return result
