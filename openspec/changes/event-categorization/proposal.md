# Proposal: Event Categorization

Intent
Provide a general, extensible system to categorize gameplay videos by semantic events (e.g. doubleKill, teamfight, baronNashor). The system will combine configurable frame sampling, a Vision-LLM analysis pipeline, an event registry with thumbnails/embeddings, and a fast inference path (ANN) to minimize LLM calls.

Scope
In scope:
- Sampling configuration and reliable frame extraction.
- Vision-LLM analysis integration and a safe stub for development.
- Automatic extraction of a single suggested event label per sampled frame.
- Event registry (JSON) storing event_id, label, thumbnails, embedding path, timestamps, confidence, and provenance.
- Embedding generation, ANN index, LRU cache, and fast-path inference.
- Conservative clustering + human-in-the-loop (HIL) CLI for merge/approval and migration tools.

Out of scope:
- Full UI; only CLI and file-based registry.
- Production-scale distributed index storage (future work).

Capabilities (new)
- sampling: Configurable frame sampling (stride/random) and reliable extraction.
- vision-llm: Wrapper around VisionLLMDetector with lazy load and graceful fallback.
- event-extraction: Parse LLM text to produce single canonical event label + confidence.
- registry: Persistent event registry with thumbnails and metadata.
- embeddings: Compute/persist embeddings and batch API.
- ann-index: ANN index with faiss/annoy/brute-force fallbacks.
- fast-path: Query ANN to skip LLM when match confident.
- clustering: Conservative clustering and merge suggestions; HIL CLI for review/merge.

Approach (high level)
- Use ffmpeg for deterministic frame extraction; sampling stride configured in config.json and CLI.
- Analyze sampled frames with VisionLLM when needed; stub used in tests/dev by default.
- From LLM text, extract a short event label via simple heuristics and store as candidate.
- Compute text embeddings (sentence-transformers preferred; OpenAI fallback) and persist.
- Build ANN index; on new video query embedding against index and skip LLM if distance < threshold.
- Use HDBSCAN/Agglomerative for clustering with conservative defaults; surface merge suggestions to the HIL CLI.

Affected areas (paths)
- event_categorization/* (new modules: sampling.py, pipeline.py, llm_wrapper.py, embeddings.py, ann_index.py, cache.py, clustering.py, index_rebuilder.py)
- learn_templates.py (wiring sampling & pipeline flags)
- tests/* (unit + light e2e)
- docs/event-categorization/ (TESTING.md, CHANGELOG, APPLY_PROGRESS_*.md)

Risks & Mitigations
- LLM hallucination → confidence thresholds, sample human review, conservative merges.
- Registry bloat → per-game quotas, pruning, merge policies.
- Performance/cost → batch inference, ANN fast-path, cached embeddings.
- Dependency fragility (faiss/hdbscan) → fallbacks (annoy, brute-force) and documented CI steps.

Rollback plan
- Revert code commits; keep registry snapshots and provide migration script to restore prior registry state. Use dry-run merges before applying.

Dependencies
- ffmpeg, Python 3.12, torch & transformers (for VisionLLM), sentence-transformers or OPENAI_API_KEY for embeddings, faiss/annoy optional for ANN.

Success Criteria
- Automated pipeline can process a sample video and produce an event registry with >=80% precision on a small labeled set (manual validation required).
- Fast-path reduces LLM calls by ≥60% on a representative dataset.
- Full test suite (unit + integration mocks) passes and TDD evidence recorded.
