import pandas as pd
import numpy as np

# Load your CSV
df = pd.read_csv('users.csv')

# The 'template' column in your CSV is a stringified list. 
# We need to turn that into actual columns for math.
# Using eval() to convert string "[1.2, 3.4...]" to a list
import ast # Use ast.literal_eval for safer string-to-list conversion

# ... inside audit.py ...
df['template_list'] = df['template'].apply(ast.literal_eval)
features_df = pd.DataFrame(df['template_list'].tolist())

# Add user_id back for grouping
features_df['user_id'] = df['__id__']

# Calculate Scores
scores = {}
global_means = features_df.drop(columns=['user_id']).mean()

for col in features_df.drop(columns=['user_id']).columns:
    # 1. Variance between different users (Inter-class)
    user_means = features_df.groupby('user_id')[col].mean()
    inter_var = ((user_means - global_means[col])**2).mean()
    
    # 2. Variance within a single user (Intra-class)
    intra_var = features_df.groupby('user_id')[col].var().mean()
    
    # 3. Final Score
    scores[col] = inter_var / (intra_var + 1e-9)

# Print results
results = pd.Series(scores).sort_values(ascending=False)
print("--- Fisher Criterion Scores (Top 10) ---")
print(results.head(10))