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

# Fill missing values in 'name' column with a suitable value, e.g., 'Unknown'
df['name'] = df['name'].fillna('Unknown')

# Since 'work' column has no missing values, no action is required for it
# If 'work' had missing values, we could fill them similarly or use a more suitable strategy based on the data

# Clean data types
# 'id' is already of type int64, which is suitable for an identifier
# 'name' and 'work' are of type object (string), which is suitable for their content

# Verify the changes
print("\nDataset After Handling Missing Values and Dropping Duplicates:")
print(df.head())
print(df.info())
print(df.describe())

# Final processed dataset is now in 'df'