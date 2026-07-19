import numpy as np

# 1. Increased alpha to 0.1 to soften the rigid 5-round boundary
def train_mahalanobis(enrollment_vectors, alpha=0.1):
    template = np.mean(enrollment_vectors, axis=0)
    cov_matrix = np.cov(enrollment_vectors, rowvar=False)
    
    regularized_cov = cov_matrix + alpha * np.eye(cov_matrix.shape[0])
    inv_cov_matrix = np.linalg.inv(regularized_cov)
    
    return template, inv_cov_matrix

# 2. Increased threshold to 8.0 to account for 19 degrees of freedom
def authenticate(live_vector, stored_template, inv_cov_matrix, threshold=8.0):
    delta = live_vector - stored_template
    distance = np.sqrt(np.dot(np.dot(delta, inv_cov_matrix), delta.T))
    
    if distance <= threshold:
        return True, distance
    else:
        return False, distance