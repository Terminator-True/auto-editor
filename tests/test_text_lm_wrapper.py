from event_categorization.text_lm_wrapper import TextLMWrapper


def test_dummy_fallback():
    wrapper = TextLMWrapper()
    res = wrapper.classify_text('An incredible double kill!')
    assert isinstance(res, list)
    assert res and res[0][0] == 'double_kill'
