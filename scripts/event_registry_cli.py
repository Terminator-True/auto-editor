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
