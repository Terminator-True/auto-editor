Slice 4 apply progress

Files changed:
- event_categorization/clustering.py (added)
- scripts/event_registry_cli.py (added)
- event_categorization/registry_merge.py (added)
- event_categorization/index_rebuilder.py (added)
- tests/test_clustering.py (added)
- tests/test_registry_merge.py (added)
- tests/test_cli_review.py (added)
- tests/test_index_rebuilder.py (added)
- docs/event-categorization/TESTING.md (added)
- docs/event-categorization/CHANGELOG_SLICE4.md (added)

Commits:
- feat(clustering): add conservative clustering and merge suggestions
- feat(cli): add human-in-the-loop CLI for review
- feat(merge): implement registry merge with dry-run and audit logs
- feat(index): async index rebuilder with locking and queue
- docs(tests): add testing notes and changelog for slice4

TDD Evidence:
| Task | Test File | RED | GREEN | REFACTOR | Notes |
|------|-----------|-----|-------|----------|-------|
| clustering | tests/test_clustering.py | written | not-run | not-run | Local tests not executed in apply environment; run py -3.12 -m pytest -q locally |
| cli | tests/test_cli_review.py | written | not-run | not-run | -- |
| merge | tests/test_registry_merge.py | written | not-run | not-run | -- |
| index_rebuilder | tests/test_index_rebuilder.py | written | not-run | not-run | -- |

Run tests locally: py -3.12 -m pytest tests/test_clustering.py -q
