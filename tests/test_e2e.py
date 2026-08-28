"""Offline end-to-end tests for the Slice 1 orchestration skeleton.

Runs the full pipeline (connect -> read -> transcribe -> LLM -> parse ->
validate -> apply) against a FakeResolve timeline, a fake LLM transport, and a
fixture SRT. Uses the real ``parse_llm_output`` and ``TimelineReader`` so the
whole chain is proven offline without any live Resolve/Ollama service.
"""

from __future__ import annotations

import json
from pathlib import Path

from davinci_automation.jsonl_logger import JsonlLogger
from davinci_automation.ollama_client import OllamaConnectionError
from davinci_automation.orchestrator import Orchestrator, validate_range
from tests.fake_ollama import FakeLLMTransport
from tests.fake_resolve import FakeResolve, FakeTimeline, make_fake_project

FIXTURE_SRT = Path(__file__).parent / "fixtures" / "test.srt"

# A 2-minute timeline: 120 s * 24 fps.
DURATION = 2880


class _FakeResolveClient:
    """Drop-in for ResolveClient so the orchestrator runs fully offline."""

    def __init__(self, resolve) -> None:
        self._resolve = resolve

    def connect(self):
        return self._resolve

    def active_project(self):
        return self._resolve.GetProjectManager().GetCurrentProject()

    def active_timeline(self):
        return self.active_project().GetCurrentTimeline()


def _make_resolve(duration: int = DURATION):
    project = make_fake_project(
        "TestProject",
        timeline_name="Timeline 1",
        tracks={1: ("video", [("Clip A", 0, 144)])},
        duration=duration,
    )
    return FakeResolve(projects={"TestProject": project})


def _events(tmp_path: Path):
    log_path = tmp_path / "run.jsonl"
    return [
        json.loads(line)["event"]
        for line in log_path.read_text(encoding="utf-8").splitlines()
    ]


# ---------------------------------------------------------------- fake timeline

def test_fake_timeline_records_markers_and_exposes_duration() -> None:
    timeline = FakeTimeline(name="T", duration=DURATION)

    assert timeline.GetEndFrame() == DURATION
    timeline.AddMarker(120)
    timeline.AddMarker(240)
    assert timeline.markers == [120, 240]


# -------------------------------------------------------------- validate_range

def test_validate_range_accepts_in_range() -> None:
    assert validate_range(0, 100, 200) is True


def test_validate_range_rejects_negative_start() -> None:
    assert validate_range(-5, 100, 200) is False


def test_validate_range_rejects_start_ge_end() -> None:
    assert validate_range(100, 100, 200) is False


def test_validate_range_rejects_end_exceeding_duration() -> None:
    assert validate_range(50, 300, 200) is False


# --------------------------------------------------------------------- full flow

def test_e2e_full_flow_marker_mode(tmp_path: Path) -> None:
    resolve = _make_resolve()
    client = _FakeResolveClient(resolve)
    transport = FakeLLMTransport()
    logger = JsonlLogger(tmp_path / "run.jsonl")

    orchestrator = Orchestrator(
        client, transport, srt_source=lambda: FIXTURE_SRT.read_text(), mode="marker"
    )

    assert orchestrator.run(logger) == 0

    timeline = resolve.GetProjectManager().GetCurrentProject().GetCurrentTimeline()
    # The valid corte range is 00:00:05:00 -> frame 120.
    assert timeline.markers == [120]

    events = _events(tmp_path)
    for stage in ("connection", "timeline", "transcription", "llm", "parse", "validate", "apply"):
        assert stage in events, f"missing stage event {stage}"

    # Only the injected fake transport was used (no live Ollama).
    assert len(transport.calls) == 1


def test_e2e_defaults_to_marker_mode(tmp_path: Path) -> None:
    resolve = _make_resolve()
    client = _FakeResolveClient(resolve)
    transport = FakeLLMTransport()
    logger = JsonlLogger(tmp_path / "run.jsonl")

    orchestrator = Orchestrator(client, transport, srt_source=lambda: FIXTURE_SRT.read_text())

    assert orchestrator.run(logger) == 0
    timeline = resolve.GetProjectManager().GetCurrentProject().GetCurrentTimeline()
    assert timeline.markers == [120]


def test_e2e_auto_mode_logs_intended_cut_without_mutation(tmp_path: Path) -> None:
    resolve = _make_resolve()
    client = _FakeResolveClient(resolve)
    transport = FakeLLMTransport()
    logger = JsonlLogger(tmp_path / "run.jsonl")

    orchestrator = Orchestrator(
        client, transport, srt_source=lambda: FIXTURE_SRT.read_text(), mode="auto"
    )

    assert orchestrator.run(logger) == 0
    timeline = resolve.GetProjectManager().GetCurrentProject().GetCurrentTimeline()
    assert timeline.markers == []  # auto mode never mutates
    assert "intended_cut" in _events(tmp_path)


def test_e2e_out_of_range_rejected_and_valid_applied(tmp_path: Path) -> None:
    resolve = _make_resolve()
    client = _FakeResolveClient(resolve)
    body = json.dumps(
        {
            "segmento": {"inicio": "00:00:01:00", "fin": "00:00:14:00"},
            "acciones": [
                {"tipo": "corte", "rango": {"inicio": "00:00:05:00", "fin": "00:00:08:00"},
                 "motivo": "valid intro"},
                {"tipo": "corte", "rango": {"inicio": "00:02:00:00", "fin": "00:02:30:00"},
                 "motivo": "beyond end"},
            ],
        }
    )
    transport = FakeLLMTransport(body=body)
    logger = JsonlLogger(tmp_path / "run.jsonl")

    orchestrator = Orchestrator(
        client, transport, srt_source=lambda: FIXTURE_SRT.read_text(), mode="marker"
    )

    assert orchestrator.run(logger) == 0
    timeline = resolve.GetProjectManager().GetCurrentProject().GetCurrentTimeline()
    assert timeline.markers == [120]  # only the in-range decision applied
    assert "range_rejected" in _events(tmp_path)


def test_e2e_llm_failure_returns_1(tmp_path: Path) -> None:
    resolve = _make_resolve()
    client = _FakeResolveClient(resolve)
    transport = FakeLLMTransport(error=OllamaConnectionError("cannot reach Ollama"))
    logger = JsonlLogger(tmp_path / "run.jsonl")

    orchestrator = Orchestrator(
        client, transport, srt_source=lambda: FIXTURE_SRT.read_text(), mode="marker"
    )

    assert orchestrator.run(logger) == 1
    assert _events(tmp_path)[-1] == "error"


def test_e2e_parse_failure_returns_1(tmp_path: Path) -> None:
    resolve = _make_resolve()
    client = _FakeResolveClient(resolve)
    transport = FakeLLMTransport(body="not valid json")
    logger = JsonlLogger(tmp_path / "run.jsonl")

    orchestrator = Orchestrator(
        client, transport, srt_source=lambda: FIXTURE_SRT.read_text(), mode="marker"
    )

    assert orchestrator.run(logger) == 1
    assert _events(tmp_path)[-1] == "error"


def test_e2e_empty_srt_returns_1(tmp_path: Path) -> None:
    resolve = _make_resolve()
    client = _FakeResolveClient(resolve)
    logger = JsonlLogger(tmp_path / "run.jsonl")

    orchestrator = Orchestrator(
        client, FakeLLMTransport(), srt_source=lambda: "", mode="marker"
    )

    assert orchestrator.run(logger) == 1
    assert _events(tmp_path)[-1] == "error"


def test_e2e_srt_without_usable_cues_returns_1(tmp_path: Path) -> None:
    resolve = _make_resolve()
    client = _FakeResolveClient(resolve)
    logger = JsonlLogger(tmp_path / "run.jsonl")

    # Only a sequence number and a timing line — no spoken text.
    srt = "1\n00:00:01,000 --> 00:00:02,000\n"
    orchestrator = Orchestrator(
        client, FakeLLMTransport(), srt_source=lambda: srt, mode="marker"
    )

    assert orchestrator.run(logger) == 1
    assert _events(tmp_path)[-1] == "error"


def test_e2e_non_corte_action_is_skipped(tmp_path: Path) -> None:
    resolve = _make_resolve()
    client = _FakeResolveClient(resolve)
    body = json.dumps(
        {
            "segmento": {"inicio": "00:00:01:00", "fin": "00:00:14:00"},
            "acciones": [
                {"tipo": "motion_graphic", "timestamp": "00:00:06:00",
                 "template": "lower-third", "parametros": {"text": "Hi"},
                 "duracion_frames": 48},
            ],
        }
    )
    transport = FakeLLMTransport(body=body)
    logger = JsonlLogger(tmp_path / "run.jsonl")

    orchestrator = Orchestrator(
        client, transport, srt_source=lambda: FIXTURE_SRT.read_text(), mode="marker"
    )

    assert orchestrator.run(logger) == 0  # non-corte action produces no marker
    timeline = resolve.GetProjectManager().GetCurrentProject().GetCurrentTimeline()
    assert timeline.markers == []