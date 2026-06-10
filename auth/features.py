import numpy as np


def extract_features(raw_data):
    """
    Extracts a 12-dimensional feature vector from raw recorder data.

    4 signals x 3 descriptors (mean, std, median) = 12 dimensions

    Signals:
      1. inter_tap_intervals
      2. reaction_latencies
      3. spatial_accuracies
      4. error_corrections

    Returns a numpy array of shape (12,)
    """
    signals = [
        raw_data["inter_tap_intervals"],
        raw_data["reaction_latencies"],
        raw_data["spatial_accuracies"],
        raw_data["error_corrections"],
    ]

    vector = []
    for signal in signals:
        arr = np.array(signal, dtype=float)
        if len(arr) == 0:
            # If signal is empty, fill with zeros
            vector.extend([0.0, 0.0, 0.0])
        else:
            vector.append(float(np.mean(arr)))
            vector.append(float(np.std(arr)))
            vector.append(float(np.median(arr)))

    return np.array(vector, dtype=float)


def average_vectors(vectors):
    """
    Averages multiple feature vectors into one template.
    Used to combine 3 enrollment rounds into a single stored template.

    vectors: list of numpy arrays of shape (12,)
    Returns: numpy array of shape (12,)
    """
    return np.mean(vectors, axis=0)


def euclidean_distance(vec_a, vec_b):
    """
    Computes normalized Euclidean distance between two feature vectors.
    Normalizes by vector length to keep distance scale consistent.
    """
    return float(np.linalg.norm(vec_a - vec_b) / len(vec_a))
