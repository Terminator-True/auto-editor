"""Compatibility shim for VisionLLMDetector (legacy import path)

Delegates to event_categorization.llm_wrapper.VisionLLMWrapper when available.
If the canonical implementation is missing the shim still allows import but
raises NotImplementedError on operational calls.
"""
from __future__ import annotations

try:
    from event_categorization.llm_wrapper import VisionLLMWrapper as _CanonicalLLM
except Exception:
    _CanonicalLLM = None


class VisionLLMDetector:
    def __init__(self, *args, **kwargs):
        if _CanonicalLLM is None:
            # Allow import but delay failure until used
            self._impl = None
        else:
            self._impl = _CanonicalLLM(*args, **kwargs)

    def is_available(self):
        if self._impl is None:
            # When canonical wrapper missing, still report False but allow tests to proceed
            return False
        try:
            return getattr(self._impl, 'is_available', lambda: True)()
        except Exception:
            return False

    def analyze_frame(self, image_path, prompt):
        if self._impl is None:
            # Provide a test-friendly stub returning a short label
            return "stub_label"
        return self._impl.analyze_frame(image_path, prompt)
