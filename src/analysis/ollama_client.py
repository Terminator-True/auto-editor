import requests
from typing import List, Dict, Any


class OllamaClient:
    def __init__(self, base_url: str = "http://localhost:11434", timeout_ms: int = 2000, retries: int = 3):
        self.base_url = base_url
        self.timeout_ms = timeout_ms
        self.retries = retries

    def get_labels(self, frames: List[Any], model: str, top_n: int = 3) -> List[Dict[str, Any]]:
        """Call Ollama API and return list of labels with confidence.

        Returns list of dicts: [{"label": str, "confidence": float}, ...]
        """
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": model,
            "input": {"frames": frames, "top_n": top_n},
        }

        # simple request without sophisticated retry for now
        r = requests.post(url, json=payload, timeout=self.timeout_ms / 1000.0)
        r.raise_for_status()
        data = r.json()

        # Expecting data["results"] or similar
        results = data.get("results") or data.get("labels") or []
        out = []
        for item in results[:top_n]:
            # support different shapes
            if isinstance(item, dict):
                label = item.get("label") or item.get("name")
                confidence = item.get("confidence") or item.get("score") or 0.0
            else:
                # fallback
                label = str(item)
                confidence = 0.0
            out.append({"label": label, "confidence": confidence})
        return out
