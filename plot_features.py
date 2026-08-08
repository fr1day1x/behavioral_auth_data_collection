import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

# Load your newly generated features
try:
    df = pd.read_csv("extracted_biometric_features.csv")
except FileNotFoundError:
    raise FileNotFoundError("Run extract_features.py first to generate the CSV!")

# Set a clean styling theme
sns.set_theme(style="whitegrid")
plt.figure(figsize=(12, 5))

# Plot 1: Reaction Time Distribution by Friend
plt.subplot(1, 2, 1)
sns.boxplot(data=df, x="participant_id", y="rx_mean", palette="Set2")
plt.title("Mean Reaction Time per Subject")
plt.xlabel("Subject ID")
plt.ylabel("Time (ms)")

# Plot 2: Dwell Time Distribution by Friend
plt.subplot(1, 2, 2)
sns.boxplot(data=df, x="participant_id", y="dwell_mean", palette="Set3")
plt.title("Mean Dwell Time per Subject")
plt.xlabel("Subject ID")
plt.ylabel("Time (ms)")

plt.tight_layout()

# Save the diagnostic visualization
plt.savefig("biometric_distributions.png", dpi=300)
print("Plot successfully saved as 'biometric_distributions.png'. Check your folder!")
plt.show()