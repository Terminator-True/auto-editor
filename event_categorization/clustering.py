"""Clustering utilities for event categorization.

Conservative defaults: avoid over-merging. This module tries HDBSCAN first
for density-aware clusters, falls back to AgglomerativeClustering when
HDBSCAN not available, and finally to a simple threshold-based clustering
using pairwise cosine similarity.

The functions are written to be testable: a descriptions mapping can be
passed during tests to avoid disk or registry access.
"""
from __future__ import annotations

import logging
from typing import List, Dict, Optional, Tuple

import math

logger = logging.getLogger(__name__)

try:
    from .embeddings import compute_embedding, batch_compute_embeddings
except Exception:  # pragma: no cover - defensive
    # allow tests to monkeypatch embeddings
    compute_embedding = None  # type: ignore
    batch_compute_embeddings = None  # type: ignore


def _cosine(a: List[float], b: List[float]) -> float:
    num = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return num / (na * nb)


def cluster_events(
    event_ids: List[str],
    descriptions: Optional[Dict[str, str]] = None,
    min_cluster_size: int = 2,
    distance_threshold: float = 0.6,
) -> List[List[str]]:
    """Cluster events by description embeddings.

    Parameters are conservative by default to reduce over-merging.

    If descriptions is provided, it should map event_id -> text. Otherwise
    callers should ensure the registry module is available to provide text.
    """
    if descriptions is None:
        # lazy import to avoid hard dependency in tests
        try:
            from . import registry

            descriptions = {eid: registry.get_event_description(eid) for eid in event_ids}
        except Exception:
            raise RuntimeError("descriptions must be provided when registry is unavailable")

    texts = [descriptions.get(eid, "") for eid in event_ids]

    # compute embeddings (batch if available)
    if batch_compute_embeddings is not None:
        try:
            embs = batch_compute_embeddings(texts)
        except Exception as e:  # pragma: no cover - fallback path
            logger.debug("batch embeddings failed: %s", e)
            embs = [compute_embedding(t) for t in texts]
    else:
        embs = [compute_embedding(t) for t in texts]

    # Try HDBSCAN if available for density clustering
    try:
        import hdbscan
        from sklearn.metrics.pairwise import cosine_distances
        import numpy as _np

        X = _np.array(embs, dtype=_np.float32)
        # hdbscan takes min_cluster_size; conservative default is 2
        clusterer = hdbscan.HDBSCAN(min_cluster_size=max(2, min_cluster_size), metric="euclidean")
        labels = clusterer.fit_predict(X)
        clusters: Dict[int, List[str]] = {}
        for lid, eid in zip(labels.tolist(), event_ids):
            clusters.setdefault(int(lid), []).append(eid)
        # label -1 are noise; we drop clusters smaller than min_cluster_size
        out = [c for k, c in clusters.items() if k != -1 and len(c) >= min_cluster_size]
        # put each noise item as singleton cluster (conservative)
        noise = [eid for lab, eid in zip(labels.tolist(), event_ids) if lab == -1]
        out.extend([[n] for n in noise])
        return out
    except Exception:
        logger.debug("hdbscan not available, falling back")

    # Fall back: AgglomerativeClustering with cosine distance
    try:
        from sklearn.cluster import AgglomerativeClustering
        import numpy as _np

        X = _np.array(embs, dtype=_np.float32)
        # Agglomerative needs number of clusters; we approximate via threshold
        # Build pairwise cosine similarity matrix and group greedily.
        n = len(X)
        sims = [[_cosine(list(X[i]), list(X[j])) for j in range(n)] for i in range(n)]
        assigned = set()
        result: List[List[str]] = []
        for i in range(n):
            if i in assigned:
                continue
            group = [i]
            for j in range(i + 1, n):
                if j in assigned:
                    continue
                if sims[i][j] >= distance_threshold:
                    group.append(j)
            for idx in group:
                assigned.add(idx)
            if len(group) >= min_cluster_size:
                result.append([event_ids[idx] for idx in group])
            else:
                # singletons
                for idx in group:
                    result.append([event_ids[idx]])
        return result
    except Exception:
        logger.debug("sklearn not available, using simple threshold clustering")

    # Last resort: simple threshold clustering based on pairwise cosine
    n = len(embs)
    assigned = set()
    clusters_out: List[List[str]] = []
    for i in range(n):
        if i in assigned:
            continue
        group = [i]
        for j in range(i + 1, n):
            if j in assigned:
                continue
            if _cosine(embs[i], embs[j]) >= distance_threshold:
                group.append(j)
        for idx in group:
            assigned.add(idx)
        if len(group) >= min_cluster_size:
            clusters_out.append([event_ids[idx] for idx in group])
        else:
            for idx in group:
                clusters_out.append([event_ids[idx]])
    return clusters_out


def merge_suggestions(
    clusters: List[List[str]],
    descriptions: Optional[Dict[str, str]] = None,
) -> List[Dict]:
    """Produce conservative merge suggestions from clusters.

    Each suggestion contains: id, members, confidence (0..1), reasons list.
    Confidence is conservative: based on max pairwise cosine sim and textual overlap.
    """
    suggestions = []
    for cid, members in enumerate(clusters):
        if len(members) < 2:
            continue
        # estimate confidence
        # load embeddings lazily via compute_embedding if descriptions provided
        emb_map = {}
        for m in members:
            text = descriptions.get(m, "") if descriptions else None
            if text is not None:
                emb_map[m] = compute_embedding(text)
        # compute max pairwise cosine
        max_sim = 0.0
        reasons = []
        mems = list(members)
        for i in range(len(mems)):
            for j in range(i + 1, len(mems)):
                a = emb_map.get(mems[i])
                b = emb_map.get(mems[j])
                if a is None or b is None:
                    continue
                s = _cosine(a, b)
                max_sim = max(max_sim, s)
                if s > 0.9:
                    reasons.append(f"cosine sim {s:.2f} between {mems[i]} and {mems[j]}")
                elif s > 0.75:
                    reasons.append(f"cosine sim {s:.2f} (moderate)")

        # textual overlap heuristic
        if descriptions:
            texts = [descriptions.get(m, "") for m in members]
            common = set(texts[0].split()) if texts else set()
            for t in texts[1:]:
                common &= set(t.split())
            if common:
                reasons.append(f"textual overlap: {', '.join(list(common)[:5])}")

        # Conservative confidence mapping
        confidence = min(0.95, max_sim * 0.9) if max_sim > 0 else 0.25
        suggestions.append({
            "id": f"sugg-{cid}",
            "members": members,
            "confidence": round(confidence, 2),
            "reasons": reasons or ["clustered by similarity"]
        })
    return suggestions
