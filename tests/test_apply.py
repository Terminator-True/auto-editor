"""RED tests for the non-destructive apply operations (Slice 3).

Covers the §3.3 contract:
- ``MarkerApplier.apply`` adds one marker per validated timestamp and never
  mutates any clip/track.
- ``AutoApplier.validate_and_log`` validates decision ranges against the real
  timeline duration, logs ``intended_cut`` for valid ranges, rejects invalid
  ranges (``range_rejected``), and never mutates the timeline.
"""

from __future__ import annotations

import json
from pathlib import Path

from davinci_automation.apply import AutoApplier, MarkerApplier
from davinci_automation.jsonl_logger import JsonlLogger
from tests.fake_resolve import FakeTimeline, make_fake_project


def _events(log_path: Path) -> list:
    return [
        json.loads(line)["event"]
        for line in log_path.read_text(encoding="utf-8").splitlines()
    ]


# --------------------------------------------------------- MarkerApplier

def test_marker_applier_records_each_timestamp() -> None:
    timeline = FakeTimeline(name="T", duration=2880)

    MarkerApplier().apply(timeline, [120, 240, 360])

    assert timeline.markers == [120, 240, 360]


def test_marker_applier_is_non_destructive() -> None:
    project = make_fake_project(
        "P",
        timeline_name="T1",
        tracks={1: ("video", [("Clip A", 0, 100), ("Clip B", 101, 200)])},
        duration=2880,
    )
    timeline = project.GetCurrentTimeline()
    track = timeline.GetTrackByIndex(1)
    original_clip_names = [c.GetName() for c in track.clips]

    MarkerApplier().apply(timeline, [50, 150])

    assert timeline.markers == [50, 150]
    # No clip/track mutation: the track mutation guard stays untouched and the
    # clip list is unchanged.
    assert track.mutations == 0
    assert [c.GetName() for c in track.clips] == original_clip_names
    assert len(track.clips) == 2


# --------------------------------------------------------- AutoApplier

def test_auto_applier_logs_intended_cut_for_valid_range(tmp_path: Path) -> None:
    logger = JsonlLogger(tmp_path / "run.jsonl")

    valid = AutoApplier().validate_and_log([(0, 100), (50, 80)], 300, logger)

    assert valid == [(0, 100), (50, 80)]
    events = _events(tmp_path / "run.jsonl")
    assert events.count("intended_cut") == 2
    assert "range_rejected" not in events


def test_auto_applier_rejects_invalid_range_and_does_not_record(tmp_path: Path) -> None:
    logger = JsonlLogger(tmp_path / "run.jsonl")

    valid = AutoApplier().validate_and_log([(0, 100), (-5, 10), (200, 200), (250, 400)], 300, logger)

    # Only the fully in-range range is accepted.
    assert valid == [(0, 100)]
    events = _events(tmp_path / "run.jsonl")
    assert events.count("intended_cut") == 1
    assert events.count("range_rejected") == 3


def test_auto_applier_never_mutates_timeline(tmp_path: Path) -> None:
    timeline = FakeTimeline(name="T", duration=300)
    logger = JsonlLogger(tmp_path / "run.jsonl")

    AutoApplier().validate_and_log([(0, 100)], 300, logger)

    assert timeline.markers == []
    assert timeline.mutations == 0