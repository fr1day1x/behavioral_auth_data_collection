import numpy as np
import math

def analyze_trajectory(trajectory, target_start, target_end):
    """
    Processes a list of [timestamp, x, y] points for a single target movement.
    """
    if len(trajectory) < 3:
        return {"efficiency": 1.0, "peak_velocity": 0.0, "mean_jerk": 0.0}
        
    times = np.array([p[0] for p in trajectory]) / 1000.0 # Convert ms to seconds
    x_coords = np.array([p[1] for p in trajectory])
    y_coords = np.array([p[2] for p in trajectory])
    
    # 1. Path Efficiency
    ideal_dist = math.hypot(target_end[0] - target_start[0], target_end[1] - target_start[1])
    actual_dist = sum(math.hypot(x_coords[i] - x_coords[i-1], y_coords[i] - y_coords[i-1]) 
                      for i in range(1, len(x_coords)))
    efficiency = ideal_dist / (actual_dist + 1e-9)
    
    # Calculate derivatives (Velocity, Acceleration, Jerk)
    dt = np.diff(times)
    dt[dt == 0] = 0.001 # Prevent division by zero
    
    vx = np.diff(x_coords) / dt
    vy = np.diff(y_coords) / dt
    velocities = np.hypot(vx, vy)
    peak_velocity = np.max(velocities)
    
    # Acceleration
    dt_2 = dt[:-1]
    ax = np.diff(vx) / dt_2
    ay = np.diff(vy) / dt_2
    
    # Jerk (Derivative of acceleration)
    dt_3 = dt_2[:-1]
    jerk_x = np.diff(ax) / dt_3
    jerk_y = np.diff(ay) / dt_3
    jerk = np.hypot(jerk_x, jerk_y)
    mean_jerk = np.mean(jerk) if len(jerk) > 0 else 0.0
    
    return {
        "efficiency": round(efficiency, 4),
        "peak_velocity": round(peak_velocity, 2),
        "mean_jerk": round(mean_jerk, 2)
    }