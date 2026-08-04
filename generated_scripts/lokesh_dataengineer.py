import pandas as pd
import numpy as np

# Assuming df is the input DataFrame
# Let's create a sample DataFrame for demonstration purposes
# df = pd.DataFrame({
#     'id': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
#     'name': ['cp', 'dn', 'rs', np.nan, 'ab', 'cd', np.nan, 'ef', 'gh', 'ij'],
#     'work': ['ai', 'ds', 'ceo', 'dev', 'dev', 'dev', 'dev', 'dev', 'dev', 'dev']
# })

# Drop duplicate rows
df = df.drop_duplicates()

# Handle missing values in the 'name' column
# Replace missing values with a suitable string, e.g., 'Unknown'
df['name'] = df['name'].fillna('Unknown')

# Clean data types
# The 'id' column is already of type int64, so no conversion is needed
# The 'name' and 'work' columns are already of type string, so no conversion is needed

# Inspect the dataset
print("Dataset Metadata:")
print("Dimensions (Rows, Cols):", df.shape)
print("Total Duplicate Rows:", df.duplicated().sum())
print("Null Counts:")
print(df.isnull().sum())
print("Schema Info:")
print(df.info())
print("Memory Usage:", df.memory_usage().sum(), "bytes")

# Describe the data
print("\nData Description:")
print(df.describe())

# Print the first 3 sample rows
print("\nFirst 3 Sample Rows:")
print(df.head(3))

# Print the final processed dataset
print("\nFinal Processed Dataset:")
print(df)