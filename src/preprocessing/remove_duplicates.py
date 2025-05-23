import pandas as pd

df = pd.read_csv('data/combined/data_04.csv')

df_cleaned = df.drop_duplicates(subset=['Year', 'State', 'County'])

df_cleaned.to_csv('data/combined/data_041.csv', index=False)