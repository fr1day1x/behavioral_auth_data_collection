import numpy as np
import pandas as pd
from pymongo import MongoClient

# Connect to your behavioral biometrics collection
client = MongoClient("mongodb+srv://kamaltalreja2007_db_user:1122334455667788@cluster0.pmgqtvt.mongodb.net/?appName=Cluster0")
db = client["behavior_biometrics"]
collection = db["raw_telemetry"]

features_list = []

for doc in collection.find():
    pid = doc.get("participant_id")
    mode = doc.get("mode")
    
    # Loop through the 3 collected rounds
    for round_idx, round_data in enumerate(doc.get("rounds", [])):
        # 1. Flatten Reaction Times
        rx_times = []
        r_data = round_data.get("reaction_times", {})
        if isinstance(r_data, dict):
            for key in ["Adjacent", "Diagonal", "Medium"]:
                rx_times.extend(r_data.get(key, []))
        else:
            rx_times = r_data
                
        # 2. Flatten Dwell Times (Fixes the TypeError)
        dwell_times = []
        d_data = round_data.get("dwell_times", {})
        if isinstance(d_data, dict):
            for key in ["Adjacent", "Diagonal", "Medium"]:
                dwell_times.extend(d_data.get(key, []))
        else:
            dwell_times = d_data
        
        # Skip if either array ended up completely empty to avoid division by zero
        if not rx_times or not dwell_times:
            continue
            
        # Build a row of statistical summaries (Features)
        features = {
            "participant_id": pid,
            "mode": mode,
            "round": round_idx,
            # Reaction Time Features
            "rx_mean": np.mean(rx_times),
            "rx_std": np.std(rx_times),
            "rx_median": np.median(rx_times),
            "rx_min": np.min(rx_times),
            "rx_max": np.max(rx_times),
            # Dwell Time Features
            "dwell_mean": np.mean(dwell_times),
            "dwell_std": np.std(dwell_times),
            "dwell_median": np.median(dwell_times),
        }
        features_list.append(features)

df = pd.DataFrame(features_list)
df.to_csv("extracted_biometric_features.csv", index=False)
print("Features successfully extracted to extracted_biometric_features.csv")