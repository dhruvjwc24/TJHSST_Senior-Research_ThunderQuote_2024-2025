import pandas as pd

file_path = 'data/combined/data_04.csv'
data = pd.read_csv(file_path)

storm_columns = data.columns[5:]
data['Total Storms'] = data[storm_columns].sum(axis=1)

columns = list(data.columns[:3]) + ['Claims Paid', 'Dollars Paid', 'Total Storms'] + list(data.columns[5:-1])
data = data[columns]

output_path = 'data/combined/storm_type_totals.csv'
data.to_csv(output_path, index=False)

print(f"Updated dataset saved to {output_path}")
