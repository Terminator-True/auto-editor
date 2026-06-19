import pytest

from event_categorization.text_classifier import TextClassifier


def test_rule_matching_preexisting():
    tc = TextClassifier(game='generic')
    res = tc.classify('You achieved VICTORY by destroying the base')
    assert res['event_label'] == 'victory'


def test_embedding_path_or_fallback(monkeypatch):
    # Mock pipeline index to return a candidate
    class DummyIndex:
        def query(self, emb, top_k=3):
            return [('double kill', 0.2)]

    import event_categorization.pipeline as pipeline
    monkeypatch.setattr(pipeline, 'get_global_index', lambda game='generic': DummyIndex())
    tc = TextClassifier(game='generic')
    res = tc.classify('some long description that should hit embedding')
    assert 'candidates' in res
