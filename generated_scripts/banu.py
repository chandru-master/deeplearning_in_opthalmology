import pandas as pd
import numpy as np

# Create a DataFrame from the given data
data = [
    {'id': 1, 'name': 'cp', 'work': 'ai'},
    {'id': 2, 'name': 'dn', 'work': 'ds'},
    {'id': 3, 'name': 'rs', 'work': 'ceo'},
    {'id': 4, 'name': np.nan, 'work': 'dev'},
    {'id': 5, 'name': 'js', 'work': 'ai'},
    {'id': 6, 'name': 'cp', 'work': 'ai'},
    {'id': 7, 'name': np.nan, 'work': 'ds'},
    {'id': 8, 'name': 'rs', 'work': 'ceo'},
    {'id': 9, 'name': 'js', 'work': 'ai'},
    {'id': 10, 'name': 'dn', 'work': 'ds'}
]
df = pd.DataFrame(data)

# Print the initial null counts
print("Initial Null Counts:")
print(df.isnull().sum())

# Clean the null values by replacing them with empty strings
df['name'] = df['name'].fillna('')

# Print the null counts after cleaning
print("\nNull Counts After Cleaning:")
print(df.isnull().sum())

# Print the descriptive analysis
print("\nDescriptive Analysis:")
print(df.describe())

# Print the first 3 rows of the cleaned DataFrame
print("\nFirst 3 Rows of Cleaned DataFrame:")
print(df.head(3))

# Save the final processed dataset back to the variable df
df = df