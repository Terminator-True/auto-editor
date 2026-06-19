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

# Backwards compatibility: expose module-level imports that older code expects
try:
    # some callers do: from detectors.template_detector import TemplateDetector
    from .template_detector import TemplateDetector as TemplateDetector
    from .vision_llm_detector import VisionLLMDetector as VisionLLMDetector
    from .silence_detector import SilenceDetector as SilenceDetector
except Exception:
    # imports already defined above; ignore failures to keep import-time safe
    pass
