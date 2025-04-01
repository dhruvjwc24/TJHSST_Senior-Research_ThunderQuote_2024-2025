import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

df = pd.read_csv('data/combined/data_03.csv')

storm_types = ['Dust', 'Flood', 'Hail', 'Hurricane', 'Heavy Rain', 'Snow', 'Thunderstorm', 'Tornado', 'Wildfire', 'Wind']

sorted_storm_types = sorted(storm_types)

df_statewise_storms = df.groupby('State')[sorted_storm_types].sum()

colors = plt.cm.rainbow(np.linspace(0, 1, len(sorted_storm_types)))

plt.figure(figsize=(12, 8))
df_statewise_storms.plot(kind='bar', stacked=True, figsize=(12, 8), color=colors)

plt.title('Total Storms by Type for Each State')
plt.ylabel('Total Number of Storms')
plt.xlabel('State')
plt.xticks(rotation=90)
plt.tight_layout()
plt.show()
