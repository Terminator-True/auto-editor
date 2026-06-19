import os
import json
from pathlib import Path
import tempfile


def test_train_creates_registry_and_thumbnail(monkeypatch, tmp_path):
    # Arrange: monkeypatch registry base to tmp_path
    monkeypatch.setenv("EVENT_REGISTRY_BASE", str(tmp_path / "event_registry"))

    # stub vision llm
    class StubLLM:
        def analyze_frame(self, path, prompt):
            return "stub_label"

    # stub embeddings
    def fake_compute_embedding(text):
        return [0.1, 0.2, 0.3]

    monkeypatch.setattr("event_categorization.pipeline.VisionLLMWrapper", lambda: StubLLM())
    monkeypatch.setattr("event_categorization.embeddings.compute_embedding", fake_compute_embedding)
    monkeypatch.setattr("event_categorization.embeddings.persist_embedding", lambda emb, eid: str(tmp_path / "embs" / f"{eid}.npy"))

    # Run learner in a tiny simulated flow: create a dummy video file path (no real ffmpeg calls)
    video = tmp_path / "video.mp4"
    video.write_text("fake")

    # Monkeypatch TemplateDetector methods used to avoid heavy ffmpeg
    import learn_templates as lt

    class DummyDetector:
        def __init__(self, ffmpeg_path):
            pass
        def get_video_resolution(self, video_path):
            return (640, 480)
        def extract_frame(self, video_path, timestamp, out_path):
            # write a tiny png-like file
            Path(out_path).write_text("pngdata")
            return True
        def denormalize_region(self, region, resolution):
            return (0, 0, resolution[0], resolution[1])
        def create_template_from_video(self, video, ts, name, region, normalized=True):
            return True

    monkeypatch.setattr("learn_templates.TemplateDetector", DummyDetector)

    learner = lt.TemplateLearner(str(video), game_type="generic", mode="hybrid")
    learner._do_register = True

    # Simulate candidate selection by calling _register_event directly
    res = learner._register_event(1.23, "generic_victory", "victory", (0.25,0.25,0.5,0.5))

    # Assert registry file exists
    reg_file = tmp_path / "event_registry" / "registry.json"
    assert reg_file.exists()
    data = json.loads(reg_file.read_text(encoding='utf-8'))
    assert len(data.get("events", [])) == 1
    evt = data["events"][0]
    assert evt["label"] in ("generic_victory", "stub_label")
    # thumbnail saved
    thumb_dir = tmp_path / "event_registry" / "thumbnails" / "generic"
    assert any(thumb_dir.iterdir())


def test_fast_path_avoids_duplicate(monkeypatch, tmp_path):
    monkeypatch.setenv("EVENT_REGISTRY_BASE", str(tmp_path / "event_registry"))

    # prepare registry with an existing event and embedding
    from event_categorization import registry as ec_registry
    evt = {
        "event_id": "generic_victory_1",
        "label": "victory",
        "game": "generic",
        "thumbnails": [],
        "embedding_path": None,
        "timestamps": [1.0],
        "confidence": "high",
        "created_at": "2026-01-01T00:00:00Z",
        "source": "test"
    }
    ec_registry.add_event(evt)

    # monkeypatch pipeline.fast_path_check to return existing match
    import event_categorization.pipeline as pipeline
    monkeypatch.setattr(pipeline, "fast_path_check", lambda text: ("generic_victory_1", 0.1))

    # monkeypatch TemplateDetector
    import learn_templates as lt
    class DummyDetector2:
        def __init__(self, ffmpeg_path): pass
        def get_video_resolution(self, video_path): return (640,480)
        def extract_frame(self, video_path, timestamp, out_path): Path(out_path).write_text("png"); return True
        def denormalize_region(self, region, resolution): return (0,0,resolution[0],resolution[1])
        def create_template_from_video(self, video, ts, name, region, normalized=True): return True

    monkeypatch.setattr("learn_templates.TemplateDetector", DummyDetector2)

    video = tmp_path / "video2.mp4"
    video.write_text("fake")
    learner = lt.TemplateLearner(str(video), game_type="generic", mode="hybrid")
    learner._do_register = True

    res = learner._register_event(2.0, "generic_victory", "victory", (0.25,0.25,0.5,0.5))
    assert res.get("fast_path") is True
    assert res.get("event_id") == "generic_victory_1"
