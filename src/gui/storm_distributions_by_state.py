import pandas as pd
import matplotlib.pyplot as plt

# Load data
df = pd.read_csv('data/combined/data_04.csv')

# List of storm types to analyze
storm_types = ['Total Storms', 'Dust', 'Flood', 'Hail', 'Hurricane', 'Heavy Rain', 'Snow', 'Thunderstorm', 'Tornado', 'Wildfire', 'Wind']

# Set up the plot grid (assuming you want 5 rows and 10 columns of subplots)
n_rows = 5
n_cols = 10

# Create a figure and axes for the subplots
fig, axes = plt.subplots(n_rows, n_cols, figsize=(20, 30))
axes = axes.flatten()  # Flatten the 2D array of axes to 1D for easier indexing

# Loop over states and plot the data in each subplot
for idx, state in enumerate(df['State'].unique()):
    df_state = df[df['State'] == state]
    df_state_means = df_state[storm_types].mean()
    
    axes[idx].bar(df_state_means.index, df_state_means.values)
    axes[idx].set_title(state)
    axes[idx].set_ylabel('Avg Storms')
    axes[idx].tick_params(axis='x', rotation=45)

# Adjust layout and display the plot
plt.tight_layout()
plt.show()
