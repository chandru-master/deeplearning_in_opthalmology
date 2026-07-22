import pandas as pd
import numpy as np

# Assuming the dataset is already loaded into the variable 'df'
# Let's create the dataset first
data = [
    {'id': 1, 'name': 'cp', 'work': 'ai'},
    {'id': 2, 'name': 'dn', 'work': 'ds'},
    {'id': 3, 'name': 'rs', 'work': 'ceo'},
    {'id': 4, 'name': np.nan, 'work': 'dev'},
    {'id': 5, 'name': 'js', 'work': 'ai'},
    {'id': 6, 'name': np.nan, 'work': 'ds'},
    {'id': 7, 'name': 'cp', 'work': 'ai'},
    {'id': 8, 'name': 'dn', 'work': 'ds'},
    {'id': 9, 'name': 'rs', 'work': 'ceo'},
    {'id': 10, 'name': 'js', 'work': 'ai'}
]

df = pd.DataFrame(data)

# Display the initial null counts
print("Initial Null Counts:")
print(df.isnull().sum())

# Display the initial descriptive analysis
print("\nInitial Descriptive Analysis:")
print(df.describe())

# Drop duplicate rows
df = df.drop_duplicates()

# Fill null values in the 'name' column with a suitable value, e.g., 'Unknown'
df['name'] = df['name'].fillna('Unknown')

# Display the updated null counts
print("\nUpdated Null Counts:")
print(df.isnull().sum())

# Display the updated descriptive analysis
print("\nUpdated Descriptive Analysis:")
print(df.describe())

# Save the final processed dataset back to the variable 'df'
df = df