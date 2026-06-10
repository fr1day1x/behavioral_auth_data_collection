import numpy as np
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from auth.features import extract_features, average_vectors, euclidean_distance


def test_feature_extraction_shape():
    """Feature vector should always be 12-dimensional."""
    raw = {
        "inter_tap_intervals": [0.3, 0.4, 0.35, 0.28, 0.5],
        "reaction_latencies": [0.45, 0.38, 0.42, 0.51, 0.39],
        "spatial_accuracies": [5.2, 3.1, 7.8, 4.4, 6.0],
        "error_corrections": [0, 1, 0, 0, 1],
    }
    vec = extract_features(raw)
    assert vec.shape == (12,), f"Expected (12,), got {vec.shape}"
    print("PASS: feature vector shape is (12,)")


def test_average_vectors():
    """Averaged template should have same shape as individual vectors."""
    vecs = [np.random.rand(12) for _ in range(3)]
    avg = average_vectors(vecs)
    assert avg.shape == (12,), f"Expected (12,), got {avg.shape}"
    print("PASS: averaged template shape is (12,)")


def test_euclidean_distance_same():
    """Distance between identical vectors should be 0."""
    vec = np.array([0.5] * 12)
    dist = euclidean_distance(vec, vec)
    assert dist == 0.0, f"Expected 0.0, got {dist}"
    print("PASS: distance between identical vectors is 0")


def test_euclidean_distance_different():
    """Distance between different vectors should be > 0."""
    vec_a = np.zeros(12)
    vec_b = np.ones(12)
    dist = euclidean_distance(vec_a, vec_b)
    assert dist > 0, f"Expected > 0, got {dist}"
    print(f"PASS: distance between different vectors is {dist:.4f}")


if __name__ == "__main__":
    test_feature_extraction_shape()
    test_average_vectors()
    test_euclidean_distance_same()
    test_euclidean_distance_different()
    print("\nAll tests passed.")
