"""Read-only enumeration of an active timeline's tracks and clips.

Only read methods of the Resolve API are invoked; no timeline, clip, or track
is created, modified, or deleted (per spec).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass(frozen=True)
class ClipInfo:
    """Identifying details for a single clip."""

    name: str
    start: int
    end: int


@dataclass(frozen=True)
class TrackInfo:
    """A timeline track and its clips."""

    index: int
    kind: str
    clips: List[ClipInfo] = field(default_factory=list)


@dataclass(frozen=True)
class ReadResult:
    """Snapshot of the active project, timeline, and its tracks."""

    project: str
    timeline: str
    tracks: List[TrackInfo] = field(default_factory=list)


class TimelineReader:
    """Enumerate tracks and clips from a timeline (read-only)."""

    def read(self, timeline: object, project_name: str) -> ReadResult:
        """Build a ``ReadResult`` from a live/fake timeline object.

        Tracks are enumerated by index; each track's clips are read via the
        item-list API. Only read methods are used.
        """
        tracks: List[TrackInfo] = []
        track_count = timeline.GetTrackCount()

        for index in range(1, track_count + 1):
            track = timeline.GetTrackByIndex(index)
            if track is None:
                continue

            clips = [
                ClipInfo(name=clip.GetName(), start=clip.GetStart(), end=clip.GetEnd())
                for clip in track.GetItemListInTrack()
            ]
            tracks.append(TrackInfo(index=track.GetIndex(), kind=track.GetKind(), clips=clips))

        return ReadResult(project=project_name, timeline=timeline.GetName(), tracks=tracks)