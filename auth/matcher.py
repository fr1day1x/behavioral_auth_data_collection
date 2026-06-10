from auth.features import euclidean_distance
from auth.template import load_template
from config import AUTH_THRESHOLD


def authenticate(participant_id, live_vector):
    """
    Compares a live feature vector against a stored template.

    Returns:
        result (bool): True if authenticated, False if rejected
        distance (float): the Euclidean distance score
        threshold (float): the threshold used
    """
    stored_template = load_template(participant_id)

    if stored_template is None:
        print(f"[Matcher] No template found for {participant_id}")
        return False, None, AUTH_THRESHOLD

    distance = euclidean_distance(stored_template, live_vector)
    result = distance <= AUTH_THRESHOLD

    print(f"[Matcher] Participant: {participant_id} | Distance: {distance:.4f} | "
          f"Threshold: {AUTH_THRESHOLD} | Result: {'ACCEPTED' if result else 'REJECTED'}")

    return result, distance, AUTH_THRESHOLD
