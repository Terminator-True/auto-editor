"""Shim for legacy detectors.SilenceDetector -> event_categorization.audio.silence_detector.SilenceDetector

If canonical implementation is absent, the shim provides a class that raises
NotImplementedError on operational calls while allowing imports to succeed.
"""
from typing import Any

try:
    from event_categorization.audio.silence_detector import SilenceDetector as _CanonicalSilenceDetector
except Exception:  # pragma: no cover - defensive
    _CanonicalSilenceDetector = None


class SilenceDetector:
    """Compatibility shim for SilenceDetector."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        if _CanonicalSilenceDetector is not None:
            self._impl = _CanonicalSilenceDetector(*args, **kwargs)
        else:
            self._impl = None

    def detect_silence(self, *args: Any, **kwargs: Any):
        if self._impl is None:
            raise NotImplementedError("Canonical SilenceDetector not found: event_categorization.audio.silence_detector.SilenceDetector")
        return self._impl.detect_silence(*args, **kwargs)


__all__ = ["SilenceDetector"]
