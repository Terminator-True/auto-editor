"""Non-destructive apply operations for the E2E prototype (Slice 3).

Isolates the §3.3 apply contract:

- ``MarkerApplier.apply`` adds one timeline marker at each validated timestamp
  via the Resolve client's ``AddMarker``. It never creates, modifies, or
  deletes a clip or track (non-destructive by default).
- ``AutoApplier.validate_and_log`` validates each decision range against the
  real timeline duration, logs ``intended_cut`` for valid ranges and
  ``range_rejected`` for invalid ones, and returns the accepted ranges without
  mutating the timeline (automatic cuts are a stub per §3.3).

Range semantics match ``orchestrator.validate_range`` (reuse): a range
``[start, end)`` is valid when ``start >= 0``, ``start < end``, and
``end <= duration``.
"""

from __future__ import annotations

from typing import List, Tuple

from davinci_automation.orchestrator import validate_range


class MarkerApplier:
    """Add timeline markers at validated timestamps (non-destructive)."""

    def apply(self, timeline, timestamps: List[int]) -> None:
        """Record one marker per timestamp; never touches clips or tracks."""
        for ts in timestamps:
            timeline.AddMarker(ts)


class AutoApplier:
    """Validated automatic-cut stub: log intended cuts, mutate nothing."""

    def validate_and_log(
        self,
        ranges: List[Tuple[int, int]],
        duration: int,
        logger,
    ) -> List[Tuple[int, int]]:
        """Validate ``ranges`` against ``duration``; log and return the valid ones.

        Each valid range is logged as an ``intended_cut``; each invalid range is
        logged as ``range_rejected`` and is never recorded. No timeline mutation.
        """
        valid: List[Tuple[int, int]] = []
        for start, end in ranges:
            if validate_range(start, end, duration):
                valid.append((start, end))
                logger.write("intended_cut", "info", start=start, end=end)
            else:
                logger.write(
                    "range_rejected",
                    "error",
                    start=start,
                    end=end,
                    duration=duration,
                )
        return valid