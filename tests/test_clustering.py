import pytest

from event_categorization import clustering


def test_cosine_and_simple_cluster():
    # small synthetic embeddings via monkeypatching compute_embedding
    descs = {"e1": "kill dragon", "e2": "dragon killed", "e3": "match start"}

    def fake_embed(t):
        if "dragon" in t:
            return [1.0, 0.0]
        return [0.0, 1.0]

    clustering.compute_embedding = fake_embed  # type: ignore
    clustering.batch_compute_embeddings = lambda texts: [fake_embed(t) for t in texts]  # type: ignore

    clusters = clustering.cluster_events(["e1", "e2", "e3"], descriptions=descs, min_cluster_size=2, distance_threshold=0.5)
    # expect e1 and e2 together
    merged = any(set(c) >= {"e1", "e2"} for c in clusters)
    assert merged

    sugg = clustering.merge_suggestions(clusters, descriptions=descs)
    assert any(len(s["members"]) >= 2 for s in sugg)
