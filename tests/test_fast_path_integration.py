import os
from event_categorization.ann_index import ANNIndex
from event_categorization.embeddings import persist_embedding
from event_categorization.pipeline import get_global_index, _GLOBAL_CACHE, fast_path_check


def test_fast_path_skips_llm(monkeypatch):
    # Prepare small index with two events: similar embeddings for 'win'
    idx = get_global_index()
    idx._ids.clear(); idx._embs.clear()
    e1 = [0.1, 0.2, 0.3]
    e2 = [0.9, 0.9, 0.9]
    idx.add('evt_win', e1)
    idx.add('evt_loss', e2)
    idx._built = False

    # stub compute_embedding to return something close to e1 for "player wins"
    import event_categorization.embeddings as emb_mod
    monkeypatch.setattr(emb_mod, 'compute_embedding', lambda t: e1)

    # ensure cache cleared
    _GLOBAL_CACHE.clear()

    res = fast_path_check("player wins", threshold=0.5)
    assert res is not None
    event_id, dist = res
    assert event_id == 'evt_win'
