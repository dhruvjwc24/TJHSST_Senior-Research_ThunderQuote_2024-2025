import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

df = pd.read_csv('data/combined/data_03.csv')

storm_types = ['Dust', 'Flood', 'Hail', 'Hurricane', 'Heavy Rain', 'Snow', 'Thunderstorm', 'Tornado', 'Wildfire', 'Wind']

# Sort the storm types alphabetically
sorted_storm_types = sorted(storm_types)

# Calculate the total storms of each type
df_storm_totals = df[sorted_storm_types].sum().sort_values(ascending=False)

# Generate a rainbow colormap with as many colors as storm types
colors = plt.cm.rainbow(np.linspace(0, 1, len(sorted_storm_types)))

plt.figure(figsize=(12, 8))
df_storm_totals.plot(kind='bar', color=colors)

plt.title('Total Storms by Type Across All States')
plt.ylabel('Total Number of Storms')
plt.xlabel('Storm Type')
plt.xticks(rotation=45)
plt.tight_layout()
plt.show()
