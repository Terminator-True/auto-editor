import json
import pytest

from src.analysis.ollama_client import OllamaClient


class DummyResponse:
    def __init__(self, json_data, status_code=200):
        self._json = json_data
        self.status_code = status_code

    def json(self):
        return self._json


def test_get_labels_parses_response(monkeypatch):
    client = OllamaClient(base_url="http://localhost:11434", timeout_ms=2000, retries=0)

    fake = {"results": [{"label": "cat", "confidence": 0.9}, {"label": "dog", "confidence": 0.1}]}

    def fake_post(url, json=None, timeout=None):
        return DummyResponse(fake)

    monkeypatch.setattr("requests.post", fake_post)

    out = client.get_labels(frames=["frame1"], model="moondream-v1", top_n=2)
    assert isinstance(out, list)
    assert out[0]["label"] == "cat"
    assert out[0]["confidence"] == 0.9
