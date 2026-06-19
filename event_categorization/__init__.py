"""event_categorization package

Lightweight package initializer so tests and imports can find the package when
running from the repository root. This file intentionally keeps imports lazy to
avoid heavy dependency loads during test discovery.
"""

__all__ = [
    # modules are imported lazily by consumers to avoid heavy startup costs
]

__version__ = "0.1.0"
