import os
from typing import List, Tuple


class TextLMWrapper:
    """Optional wrapper for a text LLM. If HF settings are present, attempt to use them.

    This wrapper is intentionally minimal and optional so tests can mock it.
    """

    def __init__(self):
        self.use_hf = os.environ.get('TEXT_LM_USE_HF') == '1'
        self.hf_token = os.environ.get('HF_TOKEN')

    def classify_text(self, description: str, top_k: int = 3) -> List[Tuple[str, float]]:
        """Return list of (label, score) candidates or empty list for fallback.

        If HF is enabled and token exists, this would call a HF model. For now, we
        provide a predictable dummy when not configured.
        """
        if self.use_hf and self.hf_token:
            # Real implementation would call huggingface inference here.
            # For safety in tests we do not call remote code and instead return empty.
            return []

        # Dummy predictable fallback (non-random) to make tests reliable
        lower = description.lower()
        if 'double kill' in lower or 'doble kill' in lower:
            return [('double_kill', 0.8)]
        if 'pentakill' in lower or 'penta' in lower:
            return [('pentakill', 0.9)]
        return []
