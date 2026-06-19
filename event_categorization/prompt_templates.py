"""Prompt templates for event-categorization.

This module provides small, pure functions to render prompt text used by the
Vision-LLM analysis and event extraction steps. The functions are intentionally
pure string builders so tests can run deterministically.

Example:
    from event_categorization.prompt_templates import render_prompt
    p = render_prompt("SuperGame", "enemy_defeated", mode="short", language="en")
    print(p)

Functions
- render_prompt(game, event_type, mode, language) -> str
- render_structured_prompt(game, event_type, mode, language) -> str

TEMPLATES: mapping of template-name -> { 'en': str, 'es': str }
"""
from typing import Literal, Dict

Language = Literal["es", "en"]

TEMPLATES: Dict[str, Dict[Language, str]] = {
    "structured": {
        "es": (
            "Por favor, analiza el siguiente evento del juego '{game}' (tipo: '{event_type}').\n"
            "Devuelve un JSON con los campos:\n"
            "  - tokens: lista de tokens de texto visibles (palabras/claves)\n"
            "  - description: una breve descripción concisa en máximo 20 palabras\n"
            "No añadas metadatos adicionales. Solo el JSON."
        ),
        "en": (
            "Please analyze the following event from game '{game}' (type: '{event_type}').\n"
            "Return a JSON with the fields:\n"
            "  - tokens: list of visible text tokens (keywords/words)\n"
            "  - description: a short concise description, max 20 words\n"
            "Do not add extra metadata. Only the JSON."
        ),
    },
    "checklist": {
        "es": (
            "Evento: '{event_type}' en juego '{game}'.\n"
            "Responde con una lista de verificación breve:\n"
            "- ¿Qué tokens de texto ves?\n"
            "- ¿Resumen breve (1-2 frases)?\n"
        ),
        "en": (
            "Event: '{event_type}' in game '{game}'.\n"
            "Reply with a short checklist:\n"
            "- What visible text tokens do you see?\n"
            "- Short summary (1-2 sentences).\n"
        ),
    },
    "short": {
        "es": "Describe brevemente el evento '{event_type}' en '{game}' (2-10 palabras).",
        "en": "Briefly describe the event '{event_type}' in '{game}' (2-10 words).",
    },
}


def render_prompt(game: str, event_type: str, mode: str = "structured", language: Language = "es") -> str:
    """Render a prompt for a given game and event_type using a named template.

    Args:
        game: Game identifier or friendly name.
        event_type: Canonical short event label (snake_case preferred).
        mode: One of the keys in TEMPLATES (structured, checklist, short).
        language: 'es' or 'en'.

    Returns:
        A formatted prompt string ready to send to the Vision-LLM.

    Example:
        >>> render_prompt('MegaGame', 'boss_defeated', mode='short', language='en')
        "Briefly describe the event 'boss_defeated' in 'MegaGame' (2-10 words)."
    """
    if mode not in TEMPLATES:
        raise ValueError(f"unknown template mode: {mode}")
    langs = TEMPLATES[mode]
    if language not in langs:
        raise ValueError(f"unsupported language: {language}")
    template = langs[language]
    return template.format(game=game, event_type=event_type)


def render_structured_prompt(game: str, event_type: str, language: Language = "es") -> str:
    """Render a structured prompt that asks for a JSON with 'tokens' and 'description'.

    The returned string is a plain-text instruction that requests a JSON object. We
    intentionally do not parse or validate the JSON here; the downstream caller
    (or tests) can decide how to parse the LLM response.

    Example:
        >>> print(render_structured_prompt('MegaGame', 'open_chest', 'en'))
        Please analyze the following event from game 'MegaGame' (type: 'open_chest').\nReturn a JSON with the fields:\n  - tokens: list of visible text tokens (keywords/words)\n  - description: a short concise description, max 20 words\nDo not add extra metadata. Only the JSON.
    """
    return render_prompt(game, event_type, mode="structured", language=language)


__all__ = ["render_prompt", "render_structured_prompt", "TEMPLATES"]
