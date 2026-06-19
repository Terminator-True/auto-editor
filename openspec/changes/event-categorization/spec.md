---
title: Event Categorization Spec
change: event-categorization
date: 2026-06-19
authors:
  - sdd-archive-cheap
---

# Event Categorization — Delta Spec (persisted from Engram)

**Source**: Engram topic_key: sdd/event-categorization/spec

**What**: Delta specification for event-categorization: sampling, Vision-LLM analysis, event extraction, registry, clustering, and fast inference.

**Why**: To automatically detect and persist canonical gameplay events (thumbnail, timestamp, confidence, description) and enable a fast registry-backed inference path to speed processing and downstream editing flows.

**Where**: Affects src/video/, src/ai/, src/events/, tests/.

---

# Summary

- Add an offline pipeline that samples frames (1-of-X), runs a Vision LLM to describe each, extracts a single canonical event label, and persists events in a per-game registry. Periodic clustering merges similar labels and creates aliases.

# Goals & Success Criteria

- Registry entries auto-created for > =90% of distinct event types in pilot dataset.
- Registry fast-path reduces per-video processing time by >30%.
- Unit & integration tests for sampling, extraction, registry CRUD, clustering.

# Non-Goals

- Live-stream/real-time detection
- Full manual curation UI (light CLI admin only)

# Data Model (event registry schema)

JSON schema for entry (stored as document or row):

{
  "id": "evt_<uuid>",
  "game_id": "game_slug_or_id",
  "label": "enemy_defeated",
  "aliases": ["killed_enemy"],
  "thumbnail_path": "events/game/evt_<uuid>.jpg",
  "timestamp_ms": 123450,
  "confidence": 0.87,
  "description": "Player defeats boss with fire spell",
  "embedding": [0.001, ...],
  "image_embedding": [0.2, ...],
  "created_at": "2026-06-19T...Z",
  "updated_at": "..."
}

# Sampling strategy

- Configurable interval X (frames or seconds) via CLI/config: --sample-frames=X or sample_interval_seconds.
- Default: X=30 frames (approx 1s at 30fps). Allow per-video override.
- Provide a sampling dry-run: `ae sample --video v.mp4 --interval 30 --dry-run` (outputs candidate frame timestamps).

# LLM Analysis API (inputs/outputs)

- POST /ai/vision/analyze
  Input: {"image_path":"...","context":{"game_id":"...","video_id":"...","timestamp_ms":12345}}
  Output: {"text":"Player opens chest; gold spills","confidence":0.92,"text_embedding":[...],"image_embedding":[...]} 

# Event extraction rules

- Derive canonical label using deterministic rules then LLM refine:
  1) Heuristic: take most frequent noun-verb pair from text (normalize to snake_case).
  2) Prompted LLM: given description and namespace, return single short label and confidence.
  3) Normalize label: lowercase, underscores, remove stopwords.
- If LLM_confidence < 0.6, mark as low_confidence (see validation policy).

# Confidence & validation policy

- Thresholds: AUTO_ACCEPT >=0.80, REVIEW_REQUIRED 0.6–0.8, REJECT/FLAG <0.6.
- Human-in-the-loop: sample N low-confidence events per 1000 events for manual review (default N=10).
- Provide CLI: `ae events review --game game1 --limit 20` to approve/merge/rename.

# Clustering & Normalization

- Use text embeddings (SBERT/clip-text) + image embeddings; cosine distance metric.
- Agglomerative clustering with threshold t_text=0.18 (cosine distance) OR image_similarity>0.85.
- Merge rule: if avg pairwise distance < threshold and combined support >= K (K=3), create canonical label and aliases.
- Store canonical_id on merged entries and add aliases list.

# Storage & retrieval

- Files: thumbnails under events/<game_id>/thumbnails/<evt_id>.jpg
- DB: events table/collection with fields per schema above; indices on (game_id,label), embedding vector index (FAISS/HNSW) for ANN.

# Fast inference path

- On new frame: compute image_embedding, lookup ANN nearest neighbors in per-game index; if nearest.distance < d_img_accept (0.12) and neighbor.confidence >= AUTO_ACCEPT, accept label; else fallback to LLM path.
- Cache embeddings per-video to disk (.cache/embeddings/<video_id>.npy).

# CLI / UX

- `ae events list --game game1 --limit 50`
- `ae events merge --game game1 --source evt_a evt_b --target evt_c`
- `ae events review --game game1 --limit 20`
- `ae sample --video v.mp4 --interval 30` (dry-run available)

# Testing & TDD plan

- Unit tests: sampling, normalization, label extraction, registry CRUD (pytest: tests/test_events_*.py)
- Integration: end-to-end on small test video (tests/integration/test_event_pipeline.py)
- Commands: `pytest tests/unit -k event` and `pytest tests/integration -k event_pipeline`

# Rollout

- Stage 1: internal pilot on 100 videos (feature-flagged, write-only registry)
- Stage 2: enable fast-path reads for 10% traffic; monitor recall/precision
- Stage 3: full rollout with pruning policy

# Backward compatibility & migration

- Add events table; existing users see no behavior change until feature flag ON.
- Migration: backfill embeddings async; safe to rollback by disabling writes.

# Risks & mitigations

- Hallucination: thresholds + human review. Cost: batch LLM + GPU caching.
- Registry bloat: per-game quotas + periodic pruning.
- Privacy: strip PII from LLM text; store only hashed ids.

---

Generated from Engram observation id: 29
