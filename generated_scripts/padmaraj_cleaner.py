import pandas as pd
import numpy as np

# Initial dataset
df = pd.DataFrame({
    'id': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
    'name': ['cp', 'dn', 'rs', np.nan, 'cp', 'dn', 'rs', np.nan, 'cp', 'dn'],
    'work': ['ai', 'ds', 'ceo', 'ai', 'ds', 'ceo', 'ai', 'ds', 'ceo', 'ai']
})

# Drop duplicate rows
df = df.drop_duplicates()

# Handle missing values
# Since 'name' is a categorical variable, we can replace missing values with a specific category, e.g., 'Unknown'
df['name'] = df['name'].fillna('Unknown')

# Clean data types
# The 'id' column is already of type int64, which is suitable for integer values
# The 'name' and 'work' columns are already of type object (string), which is suitable for categorical values

# Descriptive analysis
print("Dataset Shape:", df.shape)
print("Dataset Columns:", df.columns)
print("Dataset Data Types:\n", df.dtypes)
print("Dataset Summary Statistics:\n", df.describe())
print("Dataset Missing Values:\n", df.isnull().sum())
print("Dataset Unique Values:\n", df.nunique())

# Save the final processed dataset
df = df