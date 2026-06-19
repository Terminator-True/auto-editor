import json
import os
import re
from typing import Dict, Optional

BASE_DIR = os.path.join(os.path.dirname(__file__), 'labels')

# canonical map: normalized token -> canonical label
CANONICAL_MAP: Dict[str, str] = {
    'double kill': 'double_kill',
    'doublekill': 'double_kill',
    'doble kill': 'double_kill',
    'penta': 'pentakill',
    'pentakill': 'pentakill',
}


def _load_json(path: str) -> dict:
    try:
        with open(path, 'r', encoding='utf-8') as fh:
            return json.load(fh)
    except FileNotFoundError:
        return {}


def load_game_rules(game: str) -> dict:
    """Load rules for a given game from event_categorization/labels/{game}.json

    Returns a dict with keys like 'tokens' (list of strings) and 'regexes' (list of regex strings).
    """
    path = os.path.join(BASE_DIR, f"{game}.json")
    data = _load_json(path)
    # normalize shape
    return {
        'tokens': data.get('tokens', []),
        'regexes': data.get('regexes', []),
    }


def normalize_label(text: str, game: str = 'generic') -> Optional[str]:
    """Try to map free text to a canonical label using canonical map and game rules.

    Returns canonical label (snake_case) or None if no mapping.
    """
    if not text:
        return None
    t = text.lower()

    # 1) quick token match against canonical map
    for token, canonical in CANONICAL_MAP.items():
        if token in t:
            return canonical

    # 2) game rules
    rules = load_game_rules(game)
    for tok in rules.get('tokens', []):
        if tok.lower() in t:
            # normalize token -> snake_case
            return tok.lower().strip().replace(' ', '_')

    for rx in rules.get('regexes', []):
        try:
            if re.search(rx, text, flags=re.IGNORECASE):
                # use the regex as label hint if it contains a named group 'label'
                m = re.search(rx, text, flags=re.IGNORECASE)
                if m and 'label' in m.groupdict():
                    return m.group('label').lower().strip().replace(' ', '_')
                # fallback: return first token-like part
                return rx.lower().split('\\b')[-1].strip().replace(' ', '_') or None
        except re.error:
            continue

    return None
