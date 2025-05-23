import pandas as pd

data = pd.read_csv('data/combined/data_04.csv')

column1 = 'Claims Paid'

column2 = 'Dollars Paid'
correlation = data[column1].corr(data[column2])
print(f"Correlation of {column1} and {column2} is: {correlation}")

for column in data.columns[-11:]:
    column2 = column
    correlation = data[column1].corr(data[column2])
    print(f"Correlation of {column1} and {column2} is: {correlation}")