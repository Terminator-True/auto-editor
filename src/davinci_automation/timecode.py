"""Frames-based timecode value type for the LLM output contract.

The frozen schema (§4) expresses every temporal field as ``HH:MM:SS:FF``.
Structural string shape is validated by the JSON schema; the semantic
frame-range checks live here as a dedicated value type so ``parse_llm_output``
can rely on an already-validated ``Timecode``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Fixed frame rate assumed by the §4 contract (24 fps).
FPS = 24

_TIMECODE_RE = re.compile(r"^(\d{2}):(\d{2}):(\d{2}):(\d{2})$")


class TimecodeError(Exception):
    """A timecode string did not match ``HH:MM:SS:FF`` or a field range."""


@dataclass(frozen=True)
class Timecode:
    """A validated ``HH:MM:SS:FF`` value at ``FPS`` frames per second."""

    hour: int
    minute: int
    second: int
    frame: int

    @property
    def total_frames(self) -> int:
        """Total frame count from the timeline origin: ``((h*3600+m*60+s)*FPS)+f``."""
        return ((self.hour * 3600) + (self.minute * 60) + self.second) * FPS + self.frame


def parse_timecode(value: str) -> Timecode:
    """Parse and validate ``value`` as ``HH:MM:SS:FF``.

    Raises ``TimecodeError`` naming the offending field and expected range when
    the string is malformed or a field is out of range (FF 0-23 at 24fps).
    """
    match = _TIMECODE_RE.match(value)
    if not match:
        raise TimecodeError(
            f"invalid timecode {value!r}: expected HH:MM:SS:FF (two digits each)"
        )

    hour, minute, second, frame = (int(part) for part in match.groups())

    if minute > 59:
        raise TimecodeError(
            f"timecode {value!r}: minute {minute} out of range (expected 00-59)"
        )
    if second > 59:
        raise TimecodeError(
            f"timecode {value!r}: second {second} out of range (expected 00-59)"
        )
    if frame > FPS - 1:
        raise TimecodeError(
            f"timecode {value!r}: frame {frame} out of range (expected 00-{FPS - 1}, {FPS}fps)"
        )

    return Timecode(hour=hour, minute=minute, second=second, frame=frame)