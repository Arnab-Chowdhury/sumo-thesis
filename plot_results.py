import pandas as pd
import matplotlib.pyplot as plt

# Load the data
df = pd.read_csv('results.csv')

# Custom color palette
colors = {'west': '#1f77b4', 'south': '#ff7f0e', 'north': '#2ca02c', 'east': '#d62728'}

# Create a professional-looking plot
plt.figure(figsize=(12, 6))

# Plot each approach's mean delay evolution
for approach in df['Approach'].unique():
    approach_data = df[df['Approach'] == approach]
    
    # Plot Fixed strategy (generation 0)
    fixed = approach_data[approach_data['Strategy'] == 'Fixed']
    plt.scatter(fixed['Generation'], fixed['MeanDelay'], 
                color=colors[approach], marker='o', s=100,
                label=f'{approach} (Fixed)' if approach == 'west' else "")
    
    # Plot EGT strategy (generations 1-10)
    egt = approach_data[approach_data['Strategy'] == 'EGT']
    plt.plot(egt['Generation'], egt['MeanDelay'], 
             color=colors[approach], linestyle='--', marker='^', 
             label=f'{approach} (EGT)')

# Formatting
plt.title('Traffic Signal Optimization Results', fontsize=14, fontweight='bold')
plt.xlabel('Generation', fontsize=12)
plt.ylabel('Mean Delay (seconds)', fontsize=12)
plt.xticks(range(0, 11))
plt.grid(True, linestyle='--', alpha=0.7)
plt.legend(ncol=2, frameon=True, fontsize=10)

# Add annotations
plt.text(0.5, -0.15, f"Throughput remains 0 for all approaches\nFinal strategies: {dict(df[df['Generation'] == 10].groupby('Approach')['GreenTime'].first())}",
         ha='center', va='center', transform=plt.gca().transAxes, fontsize=9)

plt.tight_layout()
plt.savefig('traffic_optimization_results.png', dpi=300, bbox_inches='tight')
plt.close()

print("Plot saved as traffic_optimization_results.png")