"""Unit tests for event_categorization.prompt_templates

TDD-first: tests are written to define the expected behavior of the
prompt_templates module. These tests are pure and do not require external
resources.
"""
from event_categorization import prompt_templates as pt


def test_render_prompt_returns_string():
    s = pt.render_prompt("TestGame", "enemy_defeated", mode="short", language="en")
    assert isinstance(s, str)
    assert "enemy_defeated" in s


def test_render_structured_prompt_contains_tokens_field():
    s = pt.render_structured_prompt("G", "open_chest", language="es")
    # The structured template instructs the model to return a JSON with 'tokens'
    assert "tokens" in s
    assert "description" in s


def test_templates_have_both_languages():
    # Each template must have both 'es' and 'en' entries
    for name, langs in pt.TEMPLATES.items():
        assert "es" in langs, f"{name} missing es"
        assert "en" in langs, f"{name} missing en"
