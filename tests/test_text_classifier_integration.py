import os
import pytest

from event_categorization.text_classifier import TextClassifier


def test_canonical_short_circuit():
    tc = TextClassifier(game='generic')
    res = tc.classify('Amazing double kill by the player')
    assert res['event_label'] == 'double_kill'
    assert res['confidence'] >= 0.9


def test_text_lm_fallback_mock(monkeypatch):
    class DummyLM:
        def classify(self, text):
            return [('double_kill', 0.7)]

    tc = TextClassifier(model=DummyLM(), game='generic')
    res = tc.classify('some description that escapes rules')
    assert res['event_label'] == 'double_kill'
