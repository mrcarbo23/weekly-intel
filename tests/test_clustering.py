import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from src.processing.embeddings import cosine_similarity
from src.processing.clustering import _greedy_cluster


def test_cosine_similarity_identical():
    v = np.array([1.0, 0.0, 1.0])
    assert abs(cosine_similarity(v, v) - 1.0) < 1e-6


def test_cosine_similarity_orthogonal():
    v1 = np.array([1.0, 0.0])
    v2 = np.array([0.0, 1.0])
    assert abs(cosine_similarity(v1, v2)) < 1e-6


def test_greedy_cluster_groups_similar():
    # Mock items with pre-computed "embeddings" we control
    class MockItem:
        def __init__(self, idx):
            self.id = idx
            self.publish_date = None
            self.summary = type("S", (), {"embedding": None, "themes": ["AI"]})()

    items = [MockItem(i) for i in range(4)]
    # Two groups: items 0,1 are similar; items 2,3 are similar
    embeddings = [
        np.array([1.0, 0.0, 0.0]),
        np.array([0.99, 0.14, 0.0]),
        np.array([0.0, 0.0, 1.0]),
        np.array([0.0, 0.14, 0.99]),
    ]
    # Normalize
    embeddings = [e / np.linalg.norm(e) for e in embeddings]

    clusters = _greedy_cluster(items, embeddings)
    assert len(clusters) == 2
