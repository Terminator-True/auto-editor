import requests
import time
from typing import List, Dict, Any
from . import ollama_config
from ..telemetry.metrics import init_metrics


class OllamaClient:
    def __init__(self, base_url: str = None, timeout_ms: int = 2000, retries: int = 3, metrics=None):
        cfg = ollama_config.load_config()
        self.base_url = base_url or cfg.get('base_url', 'http://localhost:11434')
        self.timeout_ms = timeout_ms
        self.retries = retries
        self.metrics = metrics or init_metrics()

    def get_labels(self, frames: List[Any], model: str, top_n: int = 3) -> List[Dict[str, Any]]:
        """Call Ollama API and return list of labels with confidence.

        Returns list of dicts: [{"label": str, "confidence": float}, ...]
        """
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": model,
            "input": {"frames": frames, "top_n": top_n},
        }

        attempt = 0
        last_exc = None
        while attempt <= self.retries:
            attempt += 1
            start = time.time()
            try:
                r = requests.post(url, json=payload, timeout=self.timeout_ms / 1000.0)
                latency = time.time() - start
                try:
                    self.metrics['ollama_request_latency_seconds'].observe(latency)
                except Exception:
                    pass
                r.raise_for_status()
                self.metrics['ollama_requests_total'].inc()
                data = r.json()
                results = data.get("results") or data.get("labels") or []
                out = []
                for item in results[:top_n]:
                    if isinstance(item, dict):
                        label = item.get("label") or item.get("name")
                        confidence = item.get("confidence") or item.get("score") or 0.0
                    else:
                        label = str(item)
                        confidence = 0.0
                    out.append({"label": label, "confidence": confidence})
                return out
            except Exception as e:
                last_exc = e
                try:
                    self.metrics['ollama_requests_failed'].inc()
                except Exception:
                    pass
                backoff = 0.1 * attempt
                time.sleep(backoff)
        # exhausted retries
        raise last_exc
