"""A minimal fake of the DaVinci Resolve Python scripting API.

These classes mirror only the read-only surface used by the orchestrator so the
test suite runs entirely offline, without a live Resolve instance. None of the
methods mutate state; they exist purely so ``TimelineReader`` and friends can be
exercised deterministically.

Every method that the real API exposes as read-only returns stable values.
``mutation`` tracking on the timeline lets tests assert the orchestrator never
calls a mutating API (no timeline mutation per spec).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class FakeClip:
    """A clip on a track."""

    name: str
    start: int
    end: int

    def GetName(self) -> str:
        return self.name

    def GetStart(self) -> int:
        return self.start

    def GetEnd(self) -> int:
        return self.end


@dataclass
class FakeTrack:
    """A single timeline track containing clips."""

    index: int
    kind: str
    clips: List[FakeClip] = field(default_factory=list)
    mutations: int = 0

    def GetIndex(self) -> int:
        return self.index

    def GetKind(self) -> str:
        return self.kind

    def GetNumClips(self) -> int:
        return len(self.clips)

    def GetItemListInTrack(self) -> List[FakeClip]:
        return list(self.clips)

    def AddMarker(self, *args, **kwargs) -> None:
        """Read-only guard: this fake records mutation calls and ignores them."""
        self.mutations += 1


@dataclass
class FakeTimeline:
    """A timeline with tracks, a duration, and a marker recorder."""

    name: str
    tracks: Dict[int, FakeTrack] = field(default_factory=dict)
    mutations: int = 0
    duration: int = 0
    markers: List[int] = field(default_factory=list)

    def GetName(self) -> str:
        return self.name

    def GetTrackCount(self) -> int:
        return len(self.tracks)

    def GetTrackByIndex(self, index: int) -> Optional[FakeTrack]:
        return self.tracks.get(index)

    def GetItemListInTrack(self, track_type: str, index: int) -> List[FakeClip]:
        track = self.tracks.get(index)
        if track is None or track.kind != track_type:
            return []
        return list(track.clips)

    def GetEndFrame(self) -> int:
        """Return the timeline duration in frames (mimics the Resolve API)."""
        return self.duration

    def AddMarker(self, frame: int, *args, **kwargs) -> None:
        """Record a marker timestamp and count it as a mutation."""
        self.markers.append(frame)
        self.mutations += 1


@dataclass
class FakeProject:
    """A project exposing an active timeline."""

    name: str
    timeline: Optional[FakeTimeline] = None
    timeline_name: Optional[str] = None
    mutations: int = 0

    def GetName(self) -> str:
        return self.name

    def GetCurrentTimeline(self) -> Optional[FakeTimeline]:
        return self.timeline

    def GetTimelineByIndex(self, index: int) -> Optional[FakeTimeline]:
        return self.timeline if self.timeline and self.timeline.name == self.timeline_name else None


@dataclass
class FakeResolve:
    """Top-level Resolve object."""

    projects: Dict[str, FakeProject] = field(default_factory=dict)
    active_project_name: Optional[str] = None
    version: str = "18.6.4"
    mutations: int = 0

    def __post_init__(self) -> None:
        if self.active_project_name is None:
            self.active_project_name = next(iter(self.projects), None)

    def GetProductName(self) -> str:
        return "Resolve"

    def GetVersionString(self) -> str:
        return self.version

    def GetProjectManager(self) -> "FakeProjectManager":
        return FakeProjectManager(self)

    def AddMarker(self, *args, **kwargs) -> None:
        """Read-only guard."""
        self.mutations += 1


@dataclass
class FakeProjectManager:
    """Bridge between Resolve and its projects."""

    resolve: FakeResolve

    def GetCurrentProject(self) -> Optional[FakeProject]:
        name = self.resolve.active_project_name
        return self.resolve.projects.get(name)


def make_fake_project(
    name: str,
    timeline_name: str = "Timeline 1",
    tracks: Optional[Dict[int, Tuple[str, List[Tuple[str, int, int]]]]] = None,
    duration: int = 0,
) -> FakeProject:
    """Build a FakeProject with the given tracks.

    ``tracks`` maps track index -> (kind, [(clip_name, start, end), ...]).
    ``duration`` sets the timeline's duration in frames (``GetEndFrame``).
    """
    timeline = FakeTimeline(name=timeline_name, duration=duration)
    for index, (kind, clips) in (tracks or {}).items():
        timeline.tracks[index] = FakeTrack(
            index=index,
            kind=kind,
            clips=[FakeClip(name=n, start=s, end=e) for n, s, e in clips],
        )
    return FakeProject(name=name, timeline=timeline, timeline_name=timeline_name)
