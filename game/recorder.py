class SessionRecorder:
    def __init__(self):
        self.reset()
        
    def reset(self):
        self.reaction_times = {"Adjacent": [], "Diagonal": [], "Medium": [], "Long": [], "First": []}
        self.inter_tap_intervals = {"Adjacent": [], "Diagonal": [], "Medium": [], "Long": []}
        self.dwell_times = {"Adjacent": [], "Diagonal": [], "Medium": [], "Long": [], "First": []}
        
        self.x_offsets = []
        self.y_offsets = []
        self.errors = 0
        self.current_target_missed = False
        
        # --- NEW HIGH-FIDELITY TRACKING DATA ---
        self.trajectories = []        # Stores lists of (t, x, y) streams per target movement
        self.current_path = []        # Buffers active frame-by-frame positions
        
    def record_mouse_movement(self, timestamp, x, y):
        """Call this on every Pygame frame loop to capture the trajectory path."""
        self.current_path.append([int(timestamp), int(x), int(y)])
        
    def record_hit(self, jump_type, reaction_time, iti, dwell_time, x_offset, y_offset):
        self.reaction_times[jump_type].append(reaction_time)
        self.dwell_times[jump_type].append(dwell_time)
        
        if jump_type != "First":
            self.inter_tap_intervals[jump_type].append(iti)
            
        self.x_offsets.append(x_offset)
        self.y_offsets.append(y_offset)
        self.current_target_missed = False
        
        # --- COMMIT THE ACTIVE PATH TRAJECTORY AND RESET BUFFER ---
        self.trajectories.append(self.current_path)
        self.current_path = [] # Fresh buffer for the next target segment
        
    def record_miss(self):
        if not self.current_target_missed:
            self.errors += 1
            self.current_target_missed = True

    def get_raw_data(self):
        return {
            "reaction_times": self.reaction_times,
            "itis": self.inter_tap_intervals,
            "dwell_times": self.dwell_times,
            "x_offsets": self.x_offsets,
            "y_offsets": self.y_offsets,
            "total_errors": self.errors,
            # --- EXPANDED DATA OUTPUT ---
            "trajectories": self.trajectories
        }