from event_categorization.cache import EmbeddingCache


def test_lru_eviction():
    c = EmbeddingCache(max_size=2)
    c.put('a', [1])
    c.put('b', [2])
    assert c.get('a') == [1]
    c.put('c', [3])
    # b should be evicted because a was recently used
    assert c.get('b') is None
    assert c.get('a') == [1]
    assert c.get('c') == [3]
