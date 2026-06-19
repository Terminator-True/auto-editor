import os
from PIL import Image
import tempfile
from event_categorization.template_matching import analyze_timestamp


class DummyLLM:
    def analyze_frame(self, image_path, prompt=None):
        return "Player opens chest; gold spills"

    def classify_frame(self, image_path):
        return {
            'is_highlight': True,
            'event_type': 'loot_open',
            'confidence': 'high',
            'description': 'Player opens chest; gold spills'
        }


def test_analyze_timestamp_monkeypatch(tmp_path, monkeypatch):
    # Create a tiny synthetic video frame (image)
    img_path = tmp_path / "frame.png"
    img = Image.new('RGB', (64, 64), color=(123, 222, 100))
    img.save(img_path)

    # Monkeypatch TemplateDetector.extract_frame -> create the dummy frame
    from detectors.template_detector import TemplateDetector

    def fake_extract_frame(self, video_path, timestamp, output_path):
        # copy our generated image
        Image.open(img_path).save(output_path)
        return True

    monkeypatch.setattr(TemplateDetector, 'extract_frame', fake_extract_frame)

    # Monkeypatch VisionLLMWrapper to avoid heavy model loads
    import event_categorization.llm_wrapper as wrapper_mod

    def fake_ensure(self):
        return True

    monkeypatch.setattr(wrapper_mod.VisionLLMWrapper, '_ensure_detector', fake_ensure)
    monkeypatch.setattr(wrapper_mod.VisionLLMWrapper, 'classify_frame', lambda self, p: DummyLLM().classify_frame(p))

    # Call analyze_timestamp
    res = analyze_timestamp("dummy.mp4", 1.23, region_norm=(0.25, 0.25, 0.5, 0.5), ffmpeg_path="ffmpeg")

    assert res['timestamp'] == 1.23
    assert isinstance(res['templates_found'], list)
    assert res['llm_description'] == 'Player opens chest; gold spills'
    assert res['suggested_event'] == 'loot_open'
    assert res['confidence'] in ('high', 'medium', 'low')
