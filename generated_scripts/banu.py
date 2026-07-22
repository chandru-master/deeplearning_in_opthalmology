import pandas as pd
import numpy as np

# Assuming the dataset is already loaded into the variable 'df'
# If not, you can load it using pd.read_csv('your_file.csv')

# Print the initial null counts
print("Initial Null Counts:")
print(df.isnull().sum())

# Replace null values in the 'name' column with an empty string
df['name'] = df['name'].fillna('')

# Print the updated null counts
print("\nUpdated Null Counts:")
print(df.isnull().sum())

# Drop duplicate rows
df = df.drop_duplicates()

# Print the descriptive analysis
print("\nDescriptive Analysis:")
print(df.describe())

# Print the updated dataset
print("\nUpdated Dataset:")
print(df)

# Save the final processed dataset back to the variable 'df'
df = df