import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv('data/combined/data_04.csv')

df['Year'] = df['Year'].astype(int)

df_yearly_dollars = df.groupby('Year')['Total Storms'].sum()

plt.figure(figsize=(10, 6))
df_yearly_dollars.plot()
plt.title('Average Total Storms by Year (1980-2023)')
plt.ylabel('Average Total Storms')
plt.xlabel('Year')
plt.tight_layout()
plt.show()