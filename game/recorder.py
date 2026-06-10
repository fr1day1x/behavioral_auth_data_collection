import time


class Recorder:
    """
    Records raw behavioral signals during a game round.
    Tracks the 4 signals needed for the feature vector:
      1. Inter-tap intervals
      2. Reaction latency
      3. Spatial accuracy (click offset from target center)
      4. Error correction frequency
    """

    def __init__(self):
        self.reset()

    def reset(self):
        self.inter_tap_intervals = []   # time between consecutive taps
        self.reaction_latencies = []    # time from target appearing to tap
        self.spatial_accuracies = []    # distance from click to target center
        self.error_corrections = []     # 1 if user missed and corrected, 0 otherwise

        self._last_tap_time = None
        self._target_appear_time = None
        self._pending_error = False     # True if last click was a miss

    def on_target_appear(self):
        """Call this when a new target lights up."""
        self._target_appear_time = time.time()

    def on_correct_tap(self, offset):
        """
        Call this when the user clicks the correct target.
        offset: Euclidean distance from click to target center (pixels)
        """
        now = time.time()

        # inter-tap interval
        if self._last_tap_time is not None:
            self.inter_tap_intervals.append(now - self._last_tap_time)
        self._last_tap_time = now

        # reaction latency
        if self._target_appear_time is not None:
            self.reaction_latencies.append(now - self._target_appear_time)

        # spatial accuracy
        self.spatial_accuracies.append(offset)

        # error correction — did they miss before getting it right?
        self.error_corrections.append(1 if self._pending_error else 0)
        self._pending_error = False

    def on_incorrect_tap(self):
        """Call this when the user clicks the wrong circle."""
        self._pending_error = True

    def get_raw_data(self):
        """Returns the raw signal lists for feature extraction."""
        return {
            "inter_tap_intervals": self.inter_tap_intervals,
            "reaction_latencies": self.reaction_latencies,
            "spatial_accuracies": self.spatial_accuracies,
            "error_corrections": self.error_corrections,
        }
