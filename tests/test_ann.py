import math
from event_categorization.ann_index import ANNIndex


def test_bruteforce_add_query():
    idx = ANNIndex(dim=3)
    idx.add('a', [0.0, 0.0, 0.0])
    idx.add('b', [1.0, 0.0, 0.0])
    idx.add('c', [0.9, 0.1, 0.0])
    # Force brute force by clearing any built index
    idx._built = False
    res = idx.query([1.0, 0.0, 0.0], top_k=2)
    assert len(res) == 2
    # nearest should be 'b'
    assert res[0][0] == 'b'
    assert math.isclose(res[0][1], 0.0, abs_tol=1e-6)
