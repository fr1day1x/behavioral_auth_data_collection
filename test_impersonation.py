import pandas as pd
import numpy as np
from pymongo import MongoClient
from sklearn.preprocessing import StandardScaler
from sklearn.preprocessing import MinMaxScaler
import math

# 1. Connect to Database
MONGO_URI = "mongodb+srv://kamaltalreja2007_db_user:1122334455667788@cluster0.pmgqtvt.mongodb.net/?appName=Cluster0"

client = MongoClient(MONGO_URI)
db = client["behavior_biometrics"]
collection = db["raw_telemetry"]

processed_rows = []

# 2. Extract Data (Expanding to an 8-Dimensional Vector Space)
for doc in collection.find():
    pid = doc.get("participant_id")
    cog = doc.get("cognitive_data")
    cog_var = 0
    cog_first = 0 
    
    if cog and "familiar" in cog and "unfamiliar" in cog:
        fam = cog["familiar"].get("flight_times", [])
        unfam = cog["unfamiliar"].get("flight_times", [])
        if fam and unfam:
            cog_var = np.mean(unfam) - np.mean(fam)
            cog_first = unfam[0] - fam[0] if len(unfam)>0 and len(fam)>0 else 0

    for rnd in doc.get("rounds", []):
        itis = []
        dwells = []
        paths = rnd.get("path_efficiencies", [])
        errors = rnd.get("total_errors", 0)
        
        for jump_type in ["Adjacent", "Diagonal", "Medium", "Long"]:
            itis.extend(rnd.get("itis", {}).get(jump_type, []))
            dwells.extend(rnd.get("dwell_times", {}).get(jump_type, []))
            
        if not itis or not dwells: continue
            
        processed_rows.append({
            "participant_id": pid,
            "iti_mean": np.mean(itis),
            "dwell_mean": np.mean(dwells),
            "iti_std": np.std(itis),
            "dwell_std": np.std(dwells),
            "cog_variance": cog_var,
            "cog_first_strike": cog_first,
            "path_eff": np.mean(paths) if paths else 1.0,
            "errors": errors
        })

df = pd.DataFrame(processed_rows)

# Normalize the 8 dimensions
# Normalize the 8 dimensions while preserving absolute geometric space
features = ['iti_mean', 'dwell_mean', 'iti_std', 'dwell_std', 'cog_variance', 'cog_first_strike', 'path_eff', 'errors']
scaler = MinMaxScaler() 
df[features] = scaler.fit_transform(df[features])

# ==================================================
#  SECURITY ANALYSIS PROTOCOL
# ==================================================
# ==================================================
#  SECURITY ANALYSIS PROTOCOL (STABILIZED FOR SMALL DATA)
# ==================================================
TARGET_ID = "KAMAML_HAC"
ATTACKER_ID = "KAMAML_HAC" 

print(f"\n[SECURITY ANALYSIS] Testing Protocol...")
print(f"Target Account: {TARGET_ID}")
print(f"Attempt By: {ATTACKER_ID}\n")

target_data = df[df['participant_id'] == TARGET_ID]
if target_data.empty:
    print("Target not found in database.")
    exit()

# ENROLLMENT PHASE: Discard Round 1 (warmup). Use Rounds 2, 3, and 4 to build the template.
enrollment_data = target_data.iloc[1:4]
template = enrollment_data[features].mean()

# VERIFICATION PHASE: Isolate the test rounds
if TARGET_ID == ATTACKER_ID:
    # Test FRR using the remaining rounds (Rounds 5 and 6)
    test_data = target_data.iloc[4:] 
else:
    # Test FAR using the attacker's data
    test_data = df[df['participant_id'] == ATTACKER_ID]
    if test_data.empty:
        print("Attacker data not found in database.")
        exit()

# Safely handle empty test_data to prevent ZeroDivisionError
total_attempts = len(test_data)
if total_attempts == 0:
    print("Error: Not enough data rounds available for the verification phase.")
    exit()

# Tune this based on Prem's new 8-dimensional verification distance
# The weights are pulled directly from your Random Forest Feature Importances
weights = {
    'cog_variance': 0.2284,
    'dwell_mean': 0.2245,
    'dwell_std': 0.1742,
    'cog_first_strike': 0.1643,
    'iti_std': 0.0908,
    'iti_mean': 0.0641,
    'path_eff': 0.0536,
    'errors': 0.0001  # Nominal weight, as the ML model didn't heavily prioritize flat error counts
}

# The threshold will drop significantly because the fractional weights shrink the final sum
EUCLIDEAN_THRESHOLD = 0.31 
successful_logins = 0
total_attempts = len(test_data)

for index, attempt in test_data.iterrows():
    # Weighted Euclidean Distance across 8 dimensions
    distance = math.sqrt(sum(weights[f] * (attempt[f] - template[f])**2 for f in features))
    
    print(f"Attempt {index + 1} Weighted Distance Score: {distance:.2f}")
    
    if distance <= EUCLIDEAN_THRESHOLD:
        successful_logins += 1

print(f"\n--- RESULTS ---")
print(f"Total authentication attempts: {total_attempts}")

if TARGET_ID == ATTACKER_ID:
    print(f"Successful logins: {successful_logins}")
    rejection_rate = ((total_attempts - successful_logins) / total_attempts) * 100
    print(f"False Rejection Rate (FRR): {rejection_rate:.2f}%")
    if rejection_rate == 0:
        print("✅ USABILITY VERIFIED: Legitimate user authenticated.")
    else:
        print("⚠️ FRR DETECTED: Legitimate user locked out.")
else:
    print(f"Successful security breaches: {successful_logins}")
    far_rate = (successful_logins / total_attempts) * 100
    print(f"False Acceptance Rate (FAR): {far_rate:.2f}%")
    if far_rate == 0:
        print("✅ SYSTEM SECURE: Impersonator blocked.")
    else:
        print("⚠️ BREACH DETECTED: Impersonator bypassed security.")