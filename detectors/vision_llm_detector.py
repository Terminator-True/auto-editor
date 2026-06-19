"""Shim for legacy detectors.VisionLLMDetector -> event_categorization.llm_wrapper.VisionLLMWrapper

Provides analyze_frame and is_available that delegate to the canonical wrapper
when present. If canonical is not present, analyze_frame raises NotImplementedError
and is_available returns False.
"""
from typing import Any

try:
    from event_categorization.llm_wrapper import VisionLLMWrapper as _CanonicalVisionLLM
except Exception:  # pragma: no cover - defensive
    _CanonicalVisionLLM = None


class VisionLLMDetector:
    """Compatibility shim exposing analyze_frame and is_available."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        if _CanonicalVisionLLM is not None:
            self._impl = _CanonicalVisionLLM(*args, **kwargs)
        else:
            self._impl = None

    def analyze_frame(self, *args: Any, **kwargs: Any):
        if self._impl is None:
            raise NotImplementedError("Canonical VisionLLMWrapper not found: event_categorization.llm_wrapper.VisionLLMWrapper")
        # Delegate to the available method name(s) on the canonical impl
        if hasattr(self._impl, "analyze_frame"):
            return self._impl.analyze_frame(*args, **kwargs)
        if hasattr(self._impl, "analyze"):
            return self._impl.analyze(*args, **kwargs)
        raise NotImplementedError("Canonical VisionLLMWrapper missing analyze method")

    @staticmethod
    def is_available() -> bool:
        if _CanonicalVisionLLM is None:
            return False
        # If canonical exposes a classmethod/func to check availability, prefer it.
        if hasattr(_CanonicalVisionLLM, "is_available"):
            try:
                return bool(getattr(_CanonicalVisionLLM, "is_available")())
            except Exception:
                return False
        return True


__all__ = ["VisionLLMDetector"]
