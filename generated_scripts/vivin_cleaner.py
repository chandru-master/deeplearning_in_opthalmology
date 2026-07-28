import pandas as pd
import numpy as np

# Initial dataset
df = pd.DataFrame({
    'id': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
    'name': ['cp', 'dn', 'rs', np.nan, 'ab', 'cd', np.nan, 'ef', 'gh', 'ij'],
    'work': ['ai', 'ds', 'ceo', 'dev', 'eng', 'mgr', 'dev', 'eng', 'mgr', 'dev']
})

# Drop duplicate rows
df = df.drop_duplicates()

# Handle missing values
df['name'] = df['name'].fillna('Unknown')

# Clean data types
df['id'] = pd.to_numeric(df['id'], downcast='integer')
df['name'] = df['name'].astype(str)
df['work'] = df['work'].astype(str)

# Describe the data
print("Data Description:")
print(df.describe())

# Print data statistics
print("\nData Statistics:")
print("Count:", df.count())
print("Mean:", df.mean(numeric_only=True))
print("Median:", df.median(numeric_only=True))
print("Mode:", df.mode().iloc[0])
print("Standard Deviation:", df.std(numeric_only=True))
print("Variance:", df.var(numeric_only=True))
print("Min:", df.min(numeric_only=True))
print("Max:", df.max(numeric_only=True))

# Print data info
print("\nData Info:")
print(df.info())

# Print data head
print("\nData Head:")
print(df.head())

# Print data tail
print("\nData Tail:")
print(df.tail())