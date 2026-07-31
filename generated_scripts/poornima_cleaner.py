import pandas as pd
import numpy as np

# Initial dataset
df = pd.DataFrame({
    'id': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
    'name': ['cp', 'dn', 'rs', np.nan, 'cp', 'dn', 'rs', np.nan, 'cp', 'dn'],
    'work': ['ai', 'ds', 'ceo', 'ai', 'ds', 'ceo', 'ai', 'ds', 'ceo', 'ai']
})

# Print initial dataset metadata
print("Initial Dataset Metadata:")
print(f"Dimensions (Rows, Cols): {df.shape}")
print(f"Total Duplicate Rows: {df.duplicated().sum()}")
print(f"Null Counts: {df.isnull().sum().to_dict()}")
print(f"Schema Info: \n{df.info()}")
print(f"First 3 Sample Rows: \n{df.head(3)}")

# Drop duplicate rows
df = df.drop_duplicates()

# Handle missing values
df['name'] = df['name'].fillna('Unknown')

# Clean data types
df['id'] = df['id'].astype(int)
df['name'] = df['name'].astype(str)
df['work'] = df['work'].astype(str)

# Print processed dataset metadata
print("\nProcessed Dataset Metadata:")
print(f"Dimensions (Rows, Cols): {df.shape}")
print(f"Total Duplicate Rows: {df.duplicated().sum()}")
print(f"Null Counts: {df.isnull().sum().to_dict()}")
print(f"Schema Info: \n{df.info()}")
print(f"Processed Dataset: \n{df}")

# Print processed dataset
print("\nProcessed Dataset:")
print(df)