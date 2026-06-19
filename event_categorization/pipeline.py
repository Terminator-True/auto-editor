from typing import Optional


class VisionLLMWrapper:
    """Minimal stub for a Vision LLM wrapper used by the pipeline.

    This is intentionally a deterministic stub for the first slice: it does not
    download or run any model. analyze_frame returns a fixed response.
    """

    def __init__(self):
        self.ready = True

    def is_available(self) -> bool:
        return self.ready

    def analyze_frame(self, image_path: str, prompt: str) -> Optional[str]:
        # deterministic stubbed response for testing and wiring
        return "NO_OP_STUB"
