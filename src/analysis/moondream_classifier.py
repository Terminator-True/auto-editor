from typing import Any, Dict
import time
from ..telemetry.metrics import init_metrics


class MoondreamClassifier:
    def __init__(self, ollama_client, metadata_store, taxonomy_map: Dict[str, str] = None, calibration: Dict = None, metrics=None):
        self.client = ollama_client
        self.store = metadata_store
        self.taxonomy_map = taxonomy_map or {}
        self.calibration = calibration or {}
        self.metrics = metrics or init_metrics()

    def _apply_calibration(self, confidence: float) -> float:
        # simple Platt-like scaling: scale = a * x + b
        a = self.calibration.get('a', 1.0)
        b = self.calibration.get('b', 0.0)
        return max(0.0, min(1.0, a * confidence + b))

    def classify_frame(self, frame: Dict[str, Any]) -> Dict[str, Any]:
        frame_id = frame.get("frame_id")
        frames = [frame]
        start = time.time()
        self.metrics['classification_requests_total'].inc()
        labels = self.client.get_labels(frames=frames, model="moondream-v1", top_n=3)
        latency = time.time() - start
        try:
            self.metrics['classification_latency_seconds'].observe(latency)
        except Exception:
            pass

        if not labels:
            result = {"frame_id": frame_id, "top_label": None, "accuracy": 0.0, "labels": []}
            self.store.save_metadata(frame_id, result)
            return result

        top = labels[0]
        raw_conf = float(top.get("confidence", 0.0))
        calibrated = self._apply_calibration(raw_conf)
        mapped = self.taxonomy_map.get(top.get("label"), top.get("label")) if top.get("label") else None

        result = {
            "frame_id": frame_id,
            "top_label": mapped,
            "accuracy": calibrated,
            "raw_accuracy": raw_conf,
            "labels": labels,
        }

        self.store.save_metadata(frame_id, result)
        return result
