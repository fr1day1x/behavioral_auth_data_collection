import json
import pandas as pd
import math
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

# 1. LOAD THE ENTIRE TELEMETRY FILE
print("Loading research database...")
with open("research_raw_database.json", "r") as f:
    data = json.load(f)

# 2. SEPARATE AND FLATTEN THE MACRO METRICS
print("Processing macro-level biometric profiles...")
macro_records = []

for subject in data:
    p_id = subject["participant_id"]
    timestamp = subject["timestamp"]
    
    # Each participant has multiple sessions/rounds
    for round_idx, session in enumerate(subject["sessions"]):
        # Extract basic metrics across buckets
        record = {
            "participant_id": p_id,
            "round": round_idx + 1,
            "total_errors": session["total_errors"],
            "x_offset_mean": np.mean(session["x_offsets"]) if session["x_offsets"] else 0,
            "x_offset_std": np.std(session["x_offsets"]) if session["x_offsets"] else 0,
            "y_offset_mean": np.mean(session["y_offsets"]) if session["y_offsets"] else 0,
            "y_offset_std": np.std(session["y_offsets"]) if session["y_offsets"] else 0,
        }
        
        # Calculate overall mean for reaction times and ITIs across all buckets
        all_rt = []
        for bucket, times in session["reaction_times"].items():
            all_rt.extend(times)
        record["mean_reaction_time"] = np.mean(all_rt) if all_rt else 0
        
        all_iti = []
        for bucket, itis in session["itis"].items():
            all_iti.extend(itis)
        record["mean_inter_tap_interval"] = np.mean(all_iti) if all_iti else 0

        all_dwell = []
        for bucket, dwells in session["dwell_times"].items():
            all_dwell.extend(dwells)
        record["mean_dwell_time"] = np.mean(all_dwell) if all_dwell else 0
        
        macro_records.append(record)

df_macro = pd.DataFrame(macro_records)

# 3. EXHAUSTIVE EXPERIMENTAL KINEMATIC FEATURE ENGINE
print("Computing final multi-domain research features...")
kinematic_records = []

for subject in data:
    p_id = subject["participant_id"]
    for round_idx, session in enumerate(subject["sessions"]):
        for traj_idx, traj in enumerate(session["trajectories"]):
            if len(traj) < 6:  # Deep derivative windowing requires at least 6 raw tracking points
                continue
                
            # Unpack coordinates and timestamps (ms to seconds)
            t = np.array([p[0] for p in traj]) / 1000.0
            x = np.array([p[1] for p in traj])
            y = np.array([p[2] for p in traj])
            
            dt = np.diff(t); dt[dt == 0] = 0.001
            dx = np.diff(x); dy = np.diff(y)
            
            # Velocities
            velocities = np.hypot(dx, dy) / dt
            mean_velocity = np.mean(velocities)
            peak_velocity = np.max(velocities)
            
            # Accelerations
            dt_2 = dt[:-1]; dt_2[dt_2 == 0] = 0.001
            accelerations = np.diff(velocities) / dt_2
            peak_acceleration = np.max(np.abs(accelerations))
            
            # Jerk
            dt_3 = dt_2[:-1]; dt_3[dt_3 == 0] = 0.001
            jerk = np.diff(accelerations) / dt_3
            mean_jerk = np.mean(np.abs(jerk))
            
            # Path Efficiency & Timing Metrics
            ideal_line = np.hypot(x[-1] - x[0], y[-1] - y[0])
            actual_line = np.sum(np.hypot(dx, dy))
            path_efficiency = ideal_line / (actual_line + 1e-9)
            
            peak_idx = np.argmax(velocities)
            total_duration = t[-1] - t[0] if (t[-1] - t[0]) > 0 else 0.001
            time_to_peak = (t[peak_idx] - t[0]) / total_duration
            
            # --- NEW HIGH-LEVEL MATHEMATICAL BIOMETRICS ---
            
            # 1. Path Curvature Analysis (Geometric Radius)
            # Approximates continuous radius of curvature along the coordinate path array
            ddx = np.diff(dx) / dt[:-1]
            ddy = np.diff(dy) / dt[:-1]
            # Muted safeguard for straight line zero crossings
            num = (dx[:-1]**2 + dy[:-1]**2)**(1.5)
            den = np.abs(dx[:-1]*ddy - dy[:-1]*ddx) + 1e-6
            mean_radius_of_curvature = np.mean(num / den)

            # 2. Jitter Frequency Component (Micro-Tremor Index)
            # Standard deviation of velocity flux measures structural tremors
            jitter_index = np.std(np.diff(velocities))
            
            # 3. Spatial Angle Entropy (Directional Unpredictability)
            # Computes Shannon Entropy of the movement trajectory angles
            angles = np.arctan2(dy, dx)
            hist, _ = np.histogram(angles, bins=8, range=(-np.pi, np.pi))
            probs = hist / (np.sum(hist) + 1e-9)
            probs = probs[probs > 0]
            movement_entropy = -np.sum(probs * np.log2(probs))

            # --- STRUCTURAL DEVIATIONS ---
            direction_changes = sum(1 for i in range(len(dx) - 1) if (dx[i]*dx[i+1] + dy[i]*dy[i+1]) < 0)
            
            kinematic_records.append({
                "participant_id": p_id,
                "round": round_idx + 1,
                "trajectory_idx": traj_idx,
                "mean_velocity": round(mean_velocity, 2),
                "peak_velocity": round(peak_velocity, 2),
                "peak_acceleration": round(peak_acceleration, 2),
                "mean_jerk": round(mean_jerk, 2),
                "path_efficiency": round(path_efficiency, 4),
                "time_to_peak_ratio": round(time_to_peak, 3),
                "direction_changes": direction_changes,
                "mean_curvature_radius": round(mean_radius_of_curvature, 2),
                "jitter_index": round(jitter_index, 2),
                "movement_entropy": round(movement_entropy, 3)
            })

df_kinematics = pd.DataFrame(kinematic_records)
print("\n=== EXHAUSTIVE MATHEMATICAL KINEMATIC MATRIX COMPILED ===")
print(df_kinematics.head(3))