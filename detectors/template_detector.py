"""Compatibility shim for TemplateDetector (legacy import path)

This module re-exports a thin wrapper that delegates to the canonical
implementation in event_categorization.template_matching. The shim accepts
*args/**kwargs in constructors to remain compatible with older call sites.
"""
from __future__ import annotations
import typing

try:
    from event_categorization.template_matching import TemplateDetector as _Canonical
except Exception:
    _Canonical = None


class TemplateDetector:
    def __init__(self, *args, **kwargs):
        if _Canonical is None:
            raise NotImplementedError("Canonical TemplateDetector not available: event_categorization.template_matching missing")
        self._impl = _Canonical(*args, **kwargs)

    def get_video_resolution(self, video_path):
        return self._impl.get_video_resolution(video_path)

    def extract_frame(self, video_path, timestamp, out_path):
        return self._impl.extract_frame(video_path, timestamp, out_path)

    def denormalize_region(self, region, resolution):
        return self._impl.denormalize_region(region, resolution)

    def create_template_from_video(self, video, ts, name, region, normalized=True):
        return self._impl.create_template_from_video(video, ts, name, region, normalized=normalized)
