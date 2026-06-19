import pytest

from event_categorization.text_classifier import TextClassifier


def test_rule_match_exact():
    tc = TextClassifier()
    desc = "PLAYER achieved VICTORY after a long match"
    res = tc.classify(desc)
    assert res['event_label'] == 'victory'
    assert res['confidence'] > 0.9
    assert res['reason'].startswith('rule')


def test_embedding_map(monkeypatch):
    # prepare classifier
    tc = TextClassifier()

    # mock compute_embedding to return a dummy vector
    monkeypatch.setattr('event_categorization.embeddings.compute_embedding', lambda s: [0.1, 0.2, 0.3])

    class DummyIndex:
        def query(self, emb, top_k=3):
            # return label, distance
            return [('evt_win', 0.3), ('evt_other', 0.8)]

    monkeypatch.setattr('event_categorization.pipeline.get_global_index', lambda game='generic': DummyIndex())

    res = tc.classify('some win text')
    assert res['event_label'] == 'evt_win'
    assert 0.0 <= res['confidence'] <= 1.0
    assert res['reason'].startswith('embedding')


def test_llm_fallback_invoked(monkeypatch):
    called = {}

    class FakeModel:
        def classify(self, text):
            called['invoked'] = True
            return {'event_label': 'double_kill', 'confidence': 0.7, 'candidates': [('double_kill', 0.7)]}

    tc = TextClassifier(model=FakeModel())

    # ensure embedding path raises to force LLM
    monkeypatch.setattr('event_categorization.embeddings.compute_embedding', lambda s: (_ for _ in ()).throw(Exception('no emb')))

    res = tc.classify('an unusual event description')
    assert called.get('invoked', False) is True
    assert res['event_label'] == 'double_kill'
    assert res['reason'] == 'llm'
