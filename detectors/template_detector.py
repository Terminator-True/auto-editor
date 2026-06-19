"""Shim for legacy detectors.TemplateDetector -> event_categorization.template_matching.TemplateDetector

This module MUST import cleanly even if the canonical implementation is absent.
If the canonical implementation is present, calls are delegated 1:1. If absent,
the shim allows import/instantiation but raises NotImplementedError on operational
methods.
"""
from typing import Any

try:
    from event_categorization.template_matching import TemplateDetector as _CanonicalTemplateDetector
except Exception:  # pragma: no cover - defensive
    _CanonicalTemplateDetector = None


class TemplateDetector:
    """Compatibility shim for the legacy TemplateDetector API.

    The shim preserves the public constructor and exposes methods used by
    existing code/tests: extract_frame, get_video_resolution, denormalize_region,
    create_template_from_video. If the canonical implementation is available
    they are delegated directly; otherwise methods raise NotImplementedError.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        # Defer raising to operational calls so imports succeed even without
        # the canonical implementation.
        if _CanonicalTemplateDetector is not None:
            self._impl = _CanonicalTemplateDetector(*args, **kwargs)
        else:
            self._impl = None

    def extract_frame(self, *args: Any, **kwargs: Any):
        if self._impl is None:
            raise NotImplementedError("Canonical TemplateDetector not found: event_categorization.template_matching.TemplateDetector")
        return self._impl.extract_frame(*args, **kwargs)

    def get_video_resolution(self, *args: Any, **kwargs: Any):
        if self._impl is None:
            raise NotImplementedError("Canonical TemplateDetector not found: event_categorization.template_matching.TemplateDetector")
        return self._impl.get_video_resolution(*args, **kwargs)

    def denormalize_region(self, *args: Any, **kwargs: Any):
        if self._impl is None:
            raise NotImplementedError("Canonical TemplateDetector not found: event_categorization.template_matching.TemplateDetector")
        return self._impl.denormalize_region(*args, **kwargs)

    def create_template_from_video(self, *args: Any, **kwargs: Any):
        if self._impl is None:
            raise NotImplementedError("Canonical TemplateDetector not found: event_categorization.template_matching.TemplateDetector")
        return self._impl.create_template_from_video(*args, **kwargs)


__all__ = ["TemplateDetector"]
