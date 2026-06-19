from typing import Optional
import os
import event_categorization.embeddings as emb_mod
from event_categorization.ann_index import ANNIndex
from event_categorization.cache import EmbeddingCache
import threading


class VisionLLMWrapper:
    """Compatibility shim: prefer the real wrapper in event_categorization.llm_wrapper

    This file historically contained a stub. We keep a minimal compatibility
    shim so older imports don't break while preferring the new implementation.
    """

    def __init__(self):
        # By default we keep a lightweight NO-OP stub to avoid heavy model loads
        # during tests and developer runs. To enable the real detector set
        # environment variable EVENT_CATEGORIZATION_USE_REAL=1 in your shell.
        self._real = None
        use_real = os.environ.get("EVENT_CATEGORIZATION_USE_REAL", "0") in ("1", "true", "True")
        if use_real:
            try:
                from event_categorization.llm_wrapper import VisionLLMWrapper as RealWrapper
                self._real = RealWrapper()
            except Exception:
                # keep stub if real wrapper fails to import
                self._real = None

    def is_available(self) -> bool:
        # The shim is always "available" as a NO-OP stub; the real wrapper is opt-in
        return True

    def analyze_frame(self, image_path: str, prompt: str) -> Optional[str]:
        if self._real:
            return self._real.analyze_frame(image_path, prompt)
        # lightweight stub used in tests and when the real detector is disabled
        return "NO_OP_STUB"


# Fast-path integration: attempt to resolve via embedding ANN before running LLM
_GLOBAL_INDEX = None
_GLOBAL_CACHE = EmbeddingCache(max_size=128)
_GLOBAL_INDEX_LOCK = threading.RLock()


def get_global_index(game: str = "default", dim: int = 384) -> ANNIndex:
    global _GLOBAL_INDEX
    with _GLOBAL_INDEX_LOCK:
        if _GLOBAL_INDEX is None:
            _GLOBAL_INDEX = ANNIndex(dim=dim, game=game)
        return _GLOBAL_INDEX


def fast_path_check(suggested_event_text: Optional[str], threshold: float = 0.35):
    """Return (event_id, distance) if we can match quickly, else None."""
    if not suggested_event_text:
        return None
    emb = _GLOBAL_CACHE.get(suggested_event_text)
    if emb is None:
        try:
            # resolve compute_embedding dynamically so tests can monkeypatch
            emb = emb_mod.compute_embedding(suggested_event_text)
            _GLOBAL_CACHE.put(suggested_event_text, emb)
        except Exception:
            return None

    idx = get_global_index()
    res = idx.query(emb, top_k=1)
    if not res:
        return None
    event_id, dist = res[0]
    if dist < threshold:
        return (event_id, dist)
    return None
