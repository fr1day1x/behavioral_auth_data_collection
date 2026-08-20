import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.neural_network import MLPClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report
from pymongo import MongoClient
import warnings
warnings.filterwarnings('ignore') # Suppress basic sklearn warnings for a clean terminal

# 1. Connect to MongoDB to pull the Rich Profiles
MONGO_URI = "mongodb+srv://kamaltalreja2007_db_user:1122334455667788@cluster0.pmgqtvt.mongodb.net/?appName=Cluster0"
client = MongoClient(MONGO_URI)
db = client["behavior_biometrics"]
collection = db["raw_telemetry"]

processed_rows = []

print("Extracting multi-dimensional behavioral profiles from cloud database...")

for doc in collection.find():
    pid = doc.get("participant_id")
    
    # 1. Extract Cognitive Data (Session-level metric)
    cog = doc.get("cognitive_data")
    cog_var = 0
    cog_first = 0
    
    if cog and "familiar" in cog and "unfamiliar" in cog:
        fam_flights = cog["familiar"].get("flight_times", [])
        unfam_flights = cog["unfamiliar"].get("flight_times", [])
        
        fam_avg = np.mean(fam_flights) if fam_flights else 0
        unfam_avg = np.mean(unfam_flights) if unfam_flights else 0
        
        cog_var = unfam_avg - fam_avg
        
        if unfam_flights and fam_flights:
            cog_first = unfam_flights[0] - fam_flights[0]

    # 2. Extract Motor Data (Round-level metrics)
    for rnd in doc.get("rounds", []):
        itis = []
        dwells = []
        path_eff = rnd.get("path_efficiencies", [])
        
        for jump_type in ["Adjacent", "Diagonal", "Medium", "Long"]:
            itis.extend(rnd.get("itis", {}).get(jump_type, []))
            dwells.extend(rnd.get("dwell_times", {}).get(jump_type, []))
            
        if not itis or not dwells:
            continue
            
        # Build the Rich Feature Matrix for THIS specific round
        row_data = {
            "participant_id": pid,
            "iti_mean": np.mean(itis),
            "iti_std": np.std(itis) if len(itis) > 1 else 0,
            "dwell_mean": np.mean(dwells),
            "dwell_std": np.std(dwells) if len(dwells) > 1 else 0,
            "path_eff_mean": np.mean(path_eff) if path_eff else 1.0,
            
            # Append the session's cognitive score to this round
            "cog_variance": cog_var,
            "cog_first_strike": cog_first
        }
        
        processed_rows.append(row_data)
df = pd.DataFrame(processed_rows)


df = df.groupby("participant_id").filter(lambda x: len(x) > 1)

if len(df) < 2 or len(df["participant_id"].unique()) < 2:
    print("Error: You need at least two different test subjects in your database.")
    exit()

# Define the new rich feature columns
feature_cols = [
    "iti_mean", "iti_std", "dwell_mean", "dwell_std", 
    "path_eff_mean", "cog_variance", "cog_first_strike"
]
X = df[feature_cols]
y = df["participant_id"]

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42, stratify=y)

print("\n==================================================")
print(" ALGORITHM 1: Brown & Rogers (1993) Neural Network")
print("==================================================")
nn_clf = MLPClassifier(hidden_layer_sizes=(10,), activation='relu', solver='adam', max_iter=2000, random_state=42)
nn_clf.fit(X_train, y_train)
y_pred_nn = nn_clf.predict(X_test)
print(classification_report(y_test, y_pred_nn, zero_division=0))

print("\n==================================================")
print(" ALGORITHM 2: Ebbers & Brune (2016) Tolerance Math")
print("==================================================")
TOLERANCE_MS = 160 
enrolled_profiles = X_train.groupby(y_train).mean()

correct_authentications = 0
total_attempts = len(X_test)

for index, test_row in X_test.iterrows():
    actual_id = y_test.loc[index]
    stored_iti_mean = enrolled_profiles.loc[actual_id, "iti_mean"]
    stored_dwell_mean = enrolled_profiles.loc[actual_id, "dwell_mean"]
    
    # Validating using the new ITI (Inter-Target Interval) variable
    iti_valid = abs(test_row["iti_mean"] - stored_iti_mean) <= TOLERANCE_MS
    dwell_valid = abs(test_row["dwell_mean"] - stored_dwell_mean) <= TOLERANCE_MS
    
    if iti_valid and dwell_valid:
        correct_authentications += 1

ebbers_accuracy = correct_authentications / total_attempts
print(f"Tolerance Validation Accuracy: {ebbers_accuracy * 100:.2f}%")
print(f"Successfully authenticated {correct_authentications} out of {total_attempts} test samples using a {TOLERANCE_MS}ms window.")

print("\n==================================================")
print(" ALGORITHM 3: BioCatch Style Random Forest")
print("==================================================")
rf_clf = RandomForestClassifier(n_estimators=100, random_state=42)
rf_clf.fit(X_train, y_train)
y_pred_rf = rf_clf.predict(X_test)
print(classification_report(y_test, y_pred_rf, zero_division=0))

print("\n--- Feature Importances ---")
importances = rf_clf.feature_importances_
for feature, importance in sorted(zip(feature_cols, importances), key=lambda x: x[1], reverse=True):
    print(f"{feature.ljust(18)}: {importance * 100:.2f}% influence")

    import matplotlib.pyplot as plt

# ==================================================
#  PHASE 4: VISUALIZATION EXPORT
# ==================================================

# --- Graph 1: Feature Importances ---
print("\nGenerating Feature Importance Chart...")
plt.style.use('dark_background') # Matches your frontend aesthetic
plt.figure(figsize=(10, 6))

# Sort features for plotting
features, imps = zip(*sorted(zip(feature_cols, importances), key=lambda x: x[1], reverse=False))

# Create horizontal bar chart
bars = plt.barh(features, [i * 100 for i in imps], color='#00c8ff')
plt.title('Random Forest Feature Importances:\nCognitive vs. Motor-Kinematics', fontsize=16, fontweight='bold', pad=15)
plt.xlabel('Influence Weight (%)', fontsize=12)

# Auto-label the bars with their exact percentages
for bar in bars:
    width = bar.get_width()
    if width > 0:
        plt.text(width + 0.5, bar.get_y() + bar.get_height()/2, f'{width:.1f}%', 
                 ha='left', va='center', fontweight='bold')

plt.tight_layout()
plt.savefig('feature_importances.png', dpi=300)
plt.show()

# --- Graph 2: Cognitive Hesitation by Participant ---
print("Generating Cognitive Hesitation Variance Chart...")
plt.figure(figsize=(10, 6))

# Calculate the average hesitation variance per user
user_variance = df.groupby('participant_id')['cog_variance'].mean().sort_values(ascending=False)

# Plotting the millisecond gap
user_bars = user_variance.plot(kind='bar', color='#ff3c3c', width=0.6)
plt.title('Average Cognitive Hesitation by Test Subject', fontsize=16, fontweight='bold', pad=15)
plt.ylabel('Hesitation Variance (Milliseconds)', fontsize=12)
plt.xlabel('Participant ID', fontsize=12)
plt.xticks(rotation=45, ha='right')
plt.grid(axis='y', linestyle='--', alpha=0.3)

plt.tight_layout()
plt.savefig('cognitive_variance.png', dpi=300)
plt.show()

print("\n[SUCCESS] Visualizations saved as high-res PNG files in your project directory.")