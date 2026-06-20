import sys
import types
import pytest

def test_compute_embedding_fallback(monkeypatch):
    # simulate sentence-transformers missing and OPENAI_API_KEY absent -> deterministic fallback
    sys_modules = dict(sys.modules)
    sys.modules.pop('sentence_transformers', None)
    import importlib
    import event_categorization.embeddings as emb

    monkeypatch.delenv('OPENAI_API_KEY', raising=False)

    vec = emb.compute_embedding("hello world")
    assert isinstance(vec, list)
    assert len(vec) > 0
