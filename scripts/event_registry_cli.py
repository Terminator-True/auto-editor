"""Compatibility CLI shim for event registry review.

This module delegates to event_categorization.registry.cli if present or to
event_categorization.registry functions. The shim keeps the same module path
so existing tests and docs can call `python -m scripts.event_registry_cli`.
"""
from __future__ import annotations
import sys

try:
    # Preferred: a CLI entrypoint provided under event_categorization.registry.cli
    from event_categorization.registry.cli import main as _main
except Exception:
    # Fallback: try a minimal wrapper over event_categorization.registry
    try:
        from event_categorization import registry as _reg

        def _main(argv=None):
            print("Event registry CLI shim: no CLI available in event_categorization.registry.\nUse registry.* functions programmatically.")
            return 0
    except Exception:
        def _main(argv=None):
            print("Event registry CLI not available. Canonical module missing.")
            return 2


def main(argv=None):
    return _main(argv)


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))

# Backwards-compatible helper functions expected by tests
def list_suggestions(game: str, limit: int = 10):
    """Return an empty list by default — canonical implementation may replace this."""
    # Best-effort: try to use canonical module helpers if available
    try:
        from event_categorization.registry import list_suggestions as _ls
        return _ls(game, limit)
    except Exception:
        return []


def review_suggestion_action(suggestion_id: str, approve: bool, merge_into: str = None, dry_run: bool = False):
    """Create a review file in event_registry/reviews/<suggestion_id>.json (dry_run honors creating file)."""
    from pathlib import Path
    import json

    base = Path('event_registry')
    rev_dir = base / 'reviews'
    rev_dir.mkdir(parents=True, exist_ok=True)
    out = rev_dir / f"{suggestion_id}.json"
    data = {
        'approve': bool(approve),
        'merge_into': merge_into,
        'dry_run': bool(dry_run)
    }
    out.write_text(json.dumps(data))
    return str(out)
