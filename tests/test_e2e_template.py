import os
import tempfile
from PIL import Image
from event_categorization.template_matching import analyze_timestamp


def test_e2e_template_quick(tmp_path, monkeypatch):
    # Create a tiny synthetic video frame image to simulate ffmpeg extraction
    frame = tmp_path / "frame.png"
    Image.new('RGB', (80, 60), color=(10, 20, 30)).save(frame)

    # Patch TemplateDetector.extract_frame to write our frame
    from detectors.template_detector import TemplateDetector

    def fake_extract_frame(self, video_path, timestamp, output_path):
        Image.open(frame).save(output_path)
        return True

    monkeypatch.setattr(TemplateDetector, 'extract_frame', fake_extract_frame)

    # Patch VisionLLMWrapper to avoid loading heavy models
    import event_categorization.llm_wrapper as wrapper_mod

    monkeypatch.setattr(wrapper_mod.VisionLLMWrapper, '_ensure_detector', lambda self: True)
    monkeypatch.setattr(wrapper_mod.VisionLLMWrapper, 'classify_frame', lambda self, p: {
        'is_highlight': False,
        'event_type': 'unknown',
        'confidence': 'low',
        'description': 'no event'
    })

    res = analyze_timestamp('dummy.mp4', 0.5, ffmpeg_path='ffmpeg')
    assert 'timestamp' in res
    assert res['llm_description'] in (None, 'no event')
