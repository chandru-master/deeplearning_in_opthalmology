import pandas as pd
import numpy as np

# Assuming df is the input dataset
# Inspect the dataset
print("Initial Dataset:")
print(df.head())
print(df.info())
print(df.describe())

# Drop duplicate rows
df = df.drop_duplicates()

# Handle missing values
# Since there's only one missing value in the 'name' column, we'll fill it with a suitable value
df['name'] = df['name'].fillna('Unknown')

# Clean data types
# The 'id' column is already of type int64, and 'name' and 'work' are of type str
# No further data type cleaning is required

# Save the final processed dataset back to df
print("\nProcessed Dataset:")
print(df.head())
print(df.info())
print(df.describe())

# Save the processed dataset to a csv file
df.to_csv('processed_dataset.csv', index=False)