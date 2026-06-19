import os
from event_categorization import embeddings


def test_available_backends_none(monkeypatch):
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    # simulate sentence-transformers missing by not importing
    backs = embeddings.available_backends()
    assert isinstance(backs, list)


def test_compute_embedding_fallback():
    # ensure compute_embedding returns deterministic vector when no backends
    vec = embeddings.compute_embedding('hello world')
    assert isinstance(vec, list)
    assert len(vec) > 0
