from typing import Optional


class VisionLLMWrapper:
    """Compatibility shim: prefer the real wrapper in event_categorization.llm_wrapper

    This file historically contained a stub. We keep a minimal compatibility
    shim so older imports don't break while preferring the new implementation.
    """

    def __init__(self):
        try:
            from event_categorization.llm_wrapper import VisionLLMWrapper as RealWrapper
            self._real = RealWrapper()
        except Exception:
            self._real = None

    def is_available(self) -> bool:
        return self._real is not None

    def analyze_frame(self, image_path: str, prompt: str) -> Optional[str]:
        if self._real:
            return self._real.analyze_frame(image_path, prompt)
        return "NO_OP_STUB"
