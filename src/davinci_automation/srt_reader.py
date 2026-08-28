"""Minimal SRT subtitle parser (Slice 2).

Turns the raw text of a ``.srt`` file into an ordered list of ``SrtCue`` with
start/end timestamps expressed in seconds. Handles typical SRT structure
(sequence number, ``HH:MM:SS,mmm --> HH:MM:SS,mmm`` timecode line, one or more
text lines, blank-line separators), multi-line cue text, and cues whose
sequence numbers are omitted. Raises ``SrtError`` on empty or structurally
malformed input.

This module is parse-only (single responsibility); chunking is intentionally
left for a later change so Slice 2 stays a clean unit.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional

# Timecode line: optional trailing text is rejected; both comma and dot are
# accepted as the millisecond separator to tolerate common SRT variants.
_TIMECODE_LINE = re.compile(
    r"^(?P<sh>\d{1,2}):(?P<sm>\d{2}):(?P<ss>\d{2})[,.]"
    r"(?P<sms>\d{1,3})\s*-->\s*"
    r"(?P<eh>\d{1,2}):(?P<em>\d{2}):(?P<es>\d{2})[,.]"
    r"(?P<ems>\d{1,3})$"
)


@dataclass(frozen=True)
class SrtCue:
    """A single parsed SRT cue with ``start``/``end`` in seconds."""

    index: Optional[int]
    start: float
    end: float
    text: str


class SrtError(Exception):
    """Raised when SRT text is empty or structurally malformed."""


def _timecode_to_seconds(hours: str, minutes: str, seconds: str, millis: str) -> float:
    return (
        float(hours) * 3600
        + float(minutes) * 60
        + float(seconds)
        + int(millis) / 1000.0
    )


def _parse_cue_block(lines: List[str]) -> SrtCue:
    """Parse one non-empty cue block into an ``SrtCue``.

    A block is an optional leading sequence number, a timecode line, and zero
    or more text lines. The timecode line is mandatory; its absence or an
    unparseable format raises ``SrtError``.
    """
    index: Optional[int] = None
    cursor = 0
    if lines[0].isdigit():
        index = int(lines[0])
        cursor = 1

    if cursor >= len(lines):
        raise SrtError("SRT cue is missing its timecode line")

    match = _TIMECODE_LINE.match(lines[cursor])
    if match is None:
        raise SrtError(f"malformed timecode line: {lines[cursor]!r}")

    start = _timecode_to_seconds(
        match["sh"], match["sm"], match["ss"], match["sms"]
    )
    end = _timecode_to_seconds(match["eh"], match["em"], match["es"], match["ems"])
    text = "\n".join(lines[cursor + 1 :])
    return SrtCue(index=index, start=start, end=end, text=text)


def parse_srt(text: str) -> List[SrtCue]:
    """Parse SRT text into an ordered list of ``SrtCue`` (timestamps in seconds).

    Raises ``SrtError`` when the input is empty/whitespace-only or contains a
    structurally malformed cue.
    """
    if not text or not text.strip():
        raise SrtError("SRT text is empty")

    cues: List[SrtCue] = []
    for block in text.strip().split("\n\n"):
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if not lines:
            continue
        cues.append(_parse_cue_block(lines))
    return cues