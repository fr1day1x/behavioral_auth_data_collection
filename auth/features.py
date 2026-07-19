import numpy as np

def extract_features(raw_data):
    features = []

    # Dimensions 1-4: Reaction Times (Keep all 4 buckets)
    for bucket in ["Adjacent", "Diagonal", "Medium", "Long"]:
        arr = raw_data["reaction_times"][bucket]
        val = np.mean(arr) if len(arr) > 0 else 0.5  # Safety baseline instead of 0
        features.append(val / 1000.0)

    # Dimensions 5-8: Inter-Tap Intervals (Keep all 4 buckets)
    for bucket in ["Adjacent", "Diagonal", "Medium", "Long"]:
        arr = raw_data["itis"][bucket]
        val = np.mean(arr) if len(arr) > 0 else 0.5
        features.append(val / 2000.0)

    # --- PRUNING STARTS HERE ---
    
    # Old Dimensions 9-12 (Dwell Times): 
    # Drop 9, 10, 11 because they clone each other. 
    # Keep ONLY a single global average of ALL dwell times across the session.
    all_dwells = []
    for bucket in ["Adjacent", "Diagonal", "Medium", "Long"]:
        all_dwells.extend(raw_data["dwell_times"][bucket])
    
    global_dwell_mean = np.mean(all_dwells) if len(all_dwells) > 0 else 90.0
    features.append(global_dwell_mean / 200.0) # Now 1 feature instead of 4

    # Old Dimensions 13-15 (X-Axis Bias):
    # Drop Median (index 14) because it's highly correlated with Mean. Keep Mean and Std.
    x_arr = raw_data["x_offsets"]
    features.append((np.mean(x_arr) / 40.0) if len(x_arr) > 0 else 0.0)
    features.append((np.std(x_arr) / 40.0) if len(x_arr) > 0 else 0.0)

    # Old Dimensions 16-18 (Y-Axis Bias):
    # Drop Median (index 17) because it's highly correlated with Mean. Keep Mean and Std.
    y_arr = raw_data["y_offsets"]
    features.append((np.mean(y_arr) / 40.0) if len(y_arr) > 0 else 0.0)
    features.append((np.std(y_arr) / 40.0) if len(y_arr) > 0 else 0.0)

    # Old Dimension 19: Errors
    # Keep it to capture accuracy signature
    features.append(raw_data["total_errors"] / 5.0)

    return np.array(features)