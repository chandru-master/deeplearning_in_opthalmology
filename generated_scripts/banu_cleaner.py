import pandas as pd
import numpy as np

# Inspect the dataset
print("Initial Dataset:")
print(df.head())
print(df.info())
print(df.describe())

# Drop duplicate rows
df = df.drop_duplicates()

# Handle missing values
print("\nMissing Values Count Before Handling:")
print(df.isnull().sum())

# Replace missing values in 'name' column with a suitable value, e.g., 'Unknown'
df['name'] = df['name'].fillna('Unknown')

print("\nMissing Values Count After Handling:")
print(df.isnull().sum())

# Clean data types
# Since 'id' is already of type int64 and 'work' and 'name' are of type str, 
# no explicit data type cleaning is required for this dataset.

# Save the final processed dataset back to variable 'df'
print("\nFinal Processed Dataset:")
print(df.head())
print(df.info())
print(df.describe())