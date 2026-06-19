Apply progress (merged to Engram)

This file records that Slice 4 apply-progress for the event-categorization change
was persisted to Engram under topic_key: sdd/event-categorization/apply-progress

Summary:
- Implemented clustering, merge suggestions, registry merge tooling, HIL CLI,
  and an async index rebuilder with locking and fallbacks.
- Tests added for clustering, merge, CLI review actions, and index rebuilder.

Notes:
- Strict TDD is active for this change. Tests were written as part of the slice
  and committed, but pytest is not available in the apply environment so tests
  were not executed here. See docs/event-categorization/TESTING.md for local
  run instructions and dependency notes (hdbscan, portalocker).

Engram save: sdd/event-categorization/apply-progress
