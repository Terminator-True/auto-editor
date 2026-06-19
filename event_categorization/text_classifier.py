from typing import Optional, List, Tuple, Dict
import re

import event_categorization.embeddings as embeddings
import event_categorization.pipeline as pipeline
from event_categorization.canonical_labels import normalize_label


CANONICAL_MAP = {
    # generic canonicalization
    'victory': 'victory',
    'victories': 'victory',
    'double kill': 'double_kill',
    'doublekill': 'double_kill',
    'doble kill': 'double_kill',
    'baron': 'baron',
}


def _normalize_label(lbl: str) -> str:
    if not lbl:
        return lbl
    k = lbl.lower().strip().replace('-', ' ').replace('_', ' ')
    return CANONICAL_MAP.get(k, lbl.lower().strip().replace(' ', '_'))


class TextClassifier:
    def __init__(self, model: Optional[object] = None, rules: Optional[dict] = None, game: str = 'generic'):
        self.model = model
        self.game = game
        # rules: mapping of canonical_label -> list of tokens/regex
        self.rules = rules or self._default_rules(game)

    def _default_rules(self, game: str) -> dict:
        # small rule set for generic game
        if game == 'generic':
            return {
                'victory': [r'\bVICTORY\b', r'\bvictory\b', r'you (won|win)'],
                'double_kill': [r'\bDOUBLE KILL\b', r'\bDOUBLEKILL\b', r'\bdoble kill\b', r'\bdouble kill\b'],
                'baron': [r'\bBARON\b', r'\bbaron\b'],
            }
        return {}

    def classify(self, description: str, tokens: Optional[List[str]] = None) -> Dict:
        reason = ''
        # 1) Rule-based / canonical label quick path
        # consult canonical normalizer first (per-game overrides)
        try:
            can = normalize_label(description, game=self.game)
            if can:
                return {
                    'event_label': can,
                    'candidates': [(can, 0.99)],
                    'confidence': 0.99,
                    'reason': 'canonical'
                }
        except Exception:
            # don't fail classifier on normalization errors
            pass

        # fallback to existing rule-pattern matching
        for label, patterns in self.rules.items():
            for patt in patterns:
                try:
                    if re.search(patt, description, flags=re.IGNORECASE):
                        canonical = _normalize_label(label)
                        return {
                            'event_label': canonical,
                            'candidates': [(canonical, 0.99)],
                            'confidence': 0.99,
                            'reason': f'rule:{label}'
                        }
                except re.error:
                    # skip invalid pattern
                    continue

        # 2) Embedding similarity mapping
        try:
            emb = embeddings.compute_embedding(description)
            idx = pipeline.get_global_index(game=self.game)
            res = idx.query(emb, top_k=3)
            if res:
                # res is list of (label, distance)
                candidates = []
                for lbl, dist in res:
                    # map dist -> score: simple mapping (1 - dist) clipped
                    score = max(0.0, min(1.0, 1.0 - float(dist)))
                    candidates.append((_normalize_label(lbl), float(score)))
                # pick top
                candidates.sort(key=lambda x: x[1], reverse=True)
                top_label, top_score = candidates[0]
                # if high enough, return
                if top_score > 0.6:
                    return {
                        'event_label': top_label,
                        'candidates': candidates,
                        'confidence': float(top_score),
                        'reason': 'embedding'
                    }
                else:
                    # return embedding suggestion but low confidence
                    return {
                        'event_label': top_label,
                        'candidates': candidates,
                        'confidence': float(top_score),
                        'reason': 'embedding_low'
                    }
        except Exception:
            # embedding path unavailable — proceed to LLM
            emb = None

        # 3) LLM fallback (optional) -- consult injected model or optional wrapper from pipeline
        llm_used = None
        try:
            if self.model is not None and hasattr(self.model, 'classify'):
                llm_used = self.model.classify(description)
            else:
                # pipeline may expose an optional text LLM wrapper
                try:
                    from event_categorization.text_lm_wrapper import TextLMWrapper
                    wrapper = TextLMWrapper()
                    res = wrapper.classify_text(description, top_k=3)
                    if res:
                        # res is list of (label, score)
                        candidates = [(lbl, float(score)) for lbl, score in res]
                        candidates.sort(key=lambda x: x[1], reverse=True)
                        top_label, top_score = candidates[0]
                        return {
                            'event_label': _normalize_label(top_label),
                            'candidates': [( _normalize_label(x[0]), float(x[1])) for x in candidates],
                            'confidence': float(top_score),
                            'reason': 'text_lm'
                        }
                except Exception:
                    # optional wrapper unavailable or errored
                    llm_used = None

        except Exception:
            llm_used = None

        if llm_used:
            # accept many shapes: dict or tuple similar to previous behavior
            if isinstance(llm_used, dict):
                lbl = llm_used.get('event_label') or llm_used.get('label')
                candidates = llm_used.get('candidates') or []
                confidence = llm_used.get('confidence') or 0.0
                return {
                    'event_label': _normalize_label(lbl) if lbl else None,
                    'candidates': [( _normalize_label(x[0]), float(x[1])) for x in candidates] if candidates else ([( _normalize_label(lbl), float(confidence))] if lbl else []),
                    'confidence': float(confidence),
                    'reason': 'llm'
                }
            # fallback simple string
            if isinstance(llm_used, str):
                return {
                    'event_label': _normalize_label(llm_used),
                    'candidates': [(_normalize_label(llm_used), 0.5)],
                    'confidence': 0.5,
                    'reason': 'llm'
                }

        # final fallback: unknown
        return {
            'event_label': None,
            'candidates': [],
            'confidence': 0.0,
            'reason': 'none'
        }
