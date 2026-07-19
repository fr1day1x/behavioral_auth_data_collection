import pandas as pd
import ast

# 1. Load the data
df = pd.read_csv('users.csv')

# 2. Convert the 'template' string column into a structured DataFrame
# Each feature becomes its own column
df_features = pd.DataFrame(df['template'].apply(ast.literal_eval).tolist())

# 3. Calculate the correlation matrix
# This compares every feature against every other feature
corr_matrix = df_features.corr().abs()

# 4. Identify high correlations
# We are looking for values > 0.95 (ignoring the diagonal of 1.0s)
threshold = 0.95
high_corr = []
for i in range(len(corr_matrix.columns)):
    for j in range(i + 1, len(corr_matrix.columns)):
        if corr_matrix.iloc[i, j] > threshold:
            high_corr.append((i, j, corr_matrix.iloc[i, j]))

print("--- Highly Correlated Feature Pairs ---")
for f1, f2, val in high_corr:
    print(f"Feature {f1} and Feature {f2} are {val:.4f} correlated.")