"""
Auto-Editor Detection Modules
Multi-modal detection system for gaming highlights
"""

from .silence_detector import SilenceDetector
from .template_detector import TemplateDetector
from .vision_llm_detector import VisionLLMDetector

__all__ = [
    'SilenceDetector',
    'TemplateDetector', 
    'VisionLLMDetector'
]
