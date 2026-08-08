import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix

# 1. Load the features
df = pd.read_csv("extracted_biometric_features.csv")

# 2. Separate features (X) and target identity (y)
feature_cols = ["rx_mean", "rx_std", "rx_median", "rx_min", "rx_max", 
                "dwell_mean", "dwell_std", "dwell_median"]
X = df[feature_cols]
y = df["participant_id"]

# 3. Train/Test Split
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42, stratify=y)

# 4. Train Random Forest
print("Training behavioral biometric verification model...")
clf = RandomForestClassifier(n_estimators=100, random_state=42)
clf.fit(X_train, y_train)

# 5. Evaluate Performance
y_pred = clf.predict(X_test)
print("\n=== CLASSIFICATION REPORT ===")
print(classification_report(y_test, y_pred))

# 6. Generate Clean, Fixed Plot
sns.set_theme(style="whitegrid")
fig, axes = plt.subplots(1, 2, figsize=(14, 6))

sns.boxplot(data=df, x="participant_id", y="rx_mean", ax=axes[0], palette="Set2")
axes[0].set_title("Mean Reaction Time per Subject")
axes[0].set_xticklabels(axes[0].get_xticklabels(), rotation=30, ha="right") # Fixes overlap
axes[0].set_ylabel("Time (ms)")

sns.boxplot(data=df, x="participant_id", y="dwell_mean", ax=axes[1], palette="Set3")
axes[1].set_title("Mean Dwell Time per Subject")
axes[1].set_xticklabels(axes[1].get_xticklabels(), rotation=30, ha="right") # Fixes overlap
axes[1].set_ylabel("Time (ms)")

plt.tight_layout()
plt.savefig("biometric_distributions_fixed.png", dpi=300)
print("\nCleaned chart saved as 'biometric_distributions_fixed.png'.")
plt.show()