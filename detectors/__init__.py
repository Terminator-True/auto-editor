"""Auto-Editor detection compatibility shims package.

This package exposes legacy names so imports like `from detectors import TemplateDetector`
continue to work while the canonical implementations live under event_categorization/.
"""

from .silence_detector import SilenceDetector
from .template_detector import TemplateDetector
from .vision_llm_detector import VisionLLMDetector

__all__ = [
    "SilenceDetector",
    "TemplateDetector",
    "VisionLLMDetector",
]
