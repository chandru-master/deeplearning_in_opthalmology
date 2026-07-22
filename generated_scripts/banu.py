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
df['name'] = df['name'].fillna('Unknown')

# Clean data types
df['id'] = pd.to_numeric(df['id'], downcast='integer')
df['name'] = df['name'].astype(str)
df['work'] = df['work'].astype(str)

# Descriptive data analysis
print("Dataset Shape:", df.shape)
print("Dataset Columns:", df.columns)
print("Dataset Data Types:\n", df.dtypes)
print("Dataset Summary Statistics:\n", df.describe())
print("Dataset Missing Values:\n", df.isnull().sum())
print("Dataset Unique Values:\n", df.nunique())

# Save the final processed dataset
df = df