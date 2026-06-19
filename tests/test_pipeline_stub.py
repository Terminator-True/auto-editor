from event_categorization.pipeline import VisionLLMWrapper


def test_pipeline_stub_analyze():
    wrapper = VisionLLMWrapper()
    assert wrapper.is_available()
    resp = wrapper.analyze_frame('fake.png', 'prompt')
    assert resp == 'NO_OP_STUB'
