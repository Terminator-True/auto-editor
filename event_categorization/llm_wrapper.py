import os
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class VisionLLMWrapper:
    """Light wrapper around detectors.vision_llm_detector.VisionLLMDetector.

    - Lazily instantiates and loads the real detector on first use (load_model()).
    - Honors HF_TOKEN environment variable if present.
    - Provides analyze_frame(image_path, prompt) and classify_frame(image_path).
    - If the underlying detector or dependencies are missing, methods return None or
      graceful fallback dicts and log warnings instead of raising.
    """

    def __init__(self, ffmpeg_path: str = "ffmpeg", model_name: str = None, game_type: str = "generic"):
        self.ffmpeg_path = ffmpeg_path
        self.model_name = model_name
        self.game_type = game_type
        self._detector = None
        self._loaded = False

    def _ensure_detector(self) -> bool:
        if self._detector is not None:
            return True

        try:
            from detectors.vision_llm_detector import VisionLLMDetector, VISION_LLM_AVAILABLE
        except Exception as e:
            logger.warning("VisionLLMWrapper: failed to import VisionLLMDetector: %s", e)
            return False

        # Instantiate detector but don't force load here
        try:
            hf_token = os.environ.get("HF_TOKEN") or None
            cfg = {"hf_token": hf_token}
            self._detector = VisionLLMDetector(ffmpeg_path=self.ffmpeg_path, model_name=self.model_name or "vikhyatk/moondream2", hf_token=hf_token, game_type=self.game_type)
            return True
        except Exception as e:
            logger.warning("VisionLLMWrapper: error creating detector: %s", e)
            self._detector = None
            return False

    def load_model(self) -> bool:
        """Load the underlying model (may download weights)."""
        if not self._ensure_detector():
            return False

        if self._loaded:
            return True

        try:
            ok = self._detector.load_model()
            self._loaded = bool(ok)
            return self._loaded
        except Exception as e:
            logger.warning("VisionLLMWrapper: load_model failed: %s", e)
            return False

    def analyze_frame(self, image_path: str, prompt: Optional[str] = None) -> Optional[str]:
        """Return textual description from vision LLM or None on failure."""
        if not self._ensure_detector():
            logger.debug("VisionLLMWrapper.analyze_frame: detector not available")
            return None

        # Try to load model lazily. If loading fails, return None.
        if not self._loaded:
            if not self.load_model():
                logger.debug("VisionLLMWrapper.analyze_frame: model not loaded")
                return None

        try:
            return self._detector.analyze_frame(image_path, prompt)
        except Exception as e:
            logger.warning("VisionLLMWrapper: analyze_frame error: %s", e)
            return None

    def classify_frame(self, image_path: str) -> Optional[Dict[str, Any]]:
        """Return structured classification dict or None on failure.

        Expected shape:
        {
            'is_highlight': bool,
            'event_type': str,
            'confidence': 'high'|'medium'|'low',
            'description': str
        }
        """
        if not self._ensure_detector():
            logger.debug("VisionLLMWrapper.classify_frame: detector not available")
            return None

        if not self._loaded:
            if not self.load_model():
                logger.debug("VisionLLMWrapper.classify_frame: model not loaded")
                return None

        try:
            return self._detector.classify_highlight(image_path)
        except Exception as e:
            logger.warning("VisionLLMWrapper: classify_frame error: %s", e)
            return None
