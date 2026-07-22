import pandas as pd

# Assuming the initial dataset is available in variable 'df'
# First, let's print the initial dataset
print("Initial Dataset:")
print(df)

# Perform descriptive analysis
print("\nDescriptive Analysis:")
print(df.describe())

# Get unique values counts for each column
print("\nUnique Values Counts:")
print(df['id'].value_counts())
print(df['name'].value_counts())
print(df['work'].value_counts())

# Drop duplicate rows
df = df.drop_duplicates()

# Fill null values in 'name' column with a suitable value, e.g., 'Unknown'
df['name'] = df['name'].fillna('Unknown')

# Print the updated dataset
print("\nUpdated Dataset:")
print(df)

# Save the final processed dataset back to variable 'df'
df = df