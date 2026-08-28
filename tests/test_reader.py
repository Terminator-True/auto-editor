"""Tests for read-only timeline enumeration."""

from __future__ import annotations

from davinci_automation.reader import TimelineReader
from tests.fake_resolve import make_fake_project


def _timeline(fake_resolve):
    return fake_resolve.GetProjectManager().GetCurrentProject().GetCurrentTimeline()


def test_enumerates_tracks_and_clips(fake_resolve) -> None:
    result = TimelineReader().read(_timeline(fake_resolve), "TestProject")

    assert result.project == "TestProject"
    assert result.timeline == "Timeline 1"
    assert [t.index for t in result.tracks] == [1, 2]

    video = result.tracks[0]
    assert video.kind == "video"
    assert [(c.name, c.start, c.end) for c in video.clips] == [
        ("Clip A", 0, 24),
        ("Clip B", 25, 60),
    ]

    empty = result.tracks[1]
    assert empty.clips == []


def test_empty_timeline_returns_no_tracks() -> None:
    project = make_fake_project("P", timeline_name="T1", tracks={})
    timeline = project.GetCurrentTimeline()
    result = TimelineReader().read(timeline, "P")

    assert result.project == "P"
    assert result.timeline == "T1"
    assert result.tracks == []


def test_reader_does_not_mutate_timeline(fake_resolve) -> None:
    timeline = _timeline(fake_resolve)
    TimelineReader().read(timeline, "TestProject")

    assert timeline.mutations == 0
    for track in timeline.tracks.values():
        assert track.mutations == 0