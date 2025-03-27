import xml.etree.ElementTree as ET

# Define the edges for each approach
approaches = {
    "west": ["15491645#0"],
    "south": ["142049043#0"],
    "north": ["141821921#1"],
    "east": ["143870423"]
}

# Path to your tripinfo.xml file
file_path = r'D:\2024-12-07-18-53-54\tripinfo.xml'

# Load the XML file
tree = ET.parse(file_path)
root = tree.getroot()

# Initialize a dictionary to store timeLoss data by approach
approach_data = {key: [] for key in approaches.keys()}

# Iterate over all tripinfo elements
for trip in root.findall('tripinfo'):
    time_loss = float(trip.get('timeLoss', 0))  # Get the timeLoss attribute
    depart_lane = trip.get('departLane', '')  # Get the departLane attribute
    start_edge = depart_lane.split('_')[0]  # Extract the edge from departLane

    # Check which approach the edge belongs to
    for approach, edges in approaches.items():
        if start_edge in edges:
            approach_data[approach].append(time_loss)
            break

# Calculate statistics for each approach
print("Time Loss Statistics by Approach:")
for approach, time_losses in approach_data.items():
    if time_losses:  # Ensure there are data points to calculate
        mean_time_loss = sum(time_losses) / len(time_losses)
        max_time_loss = max(time_losses)
        min_time_loss = min(time_losses)
        vehicle_count = len(time_losses)
        print(f"  {approach.capitalize()} Approach:")
        print(f"    Mean Time Loss: {mean_time_loss:.2f} seconds")
        print(f"    Max Time Loss: {max_time_loss:.2f} seconds")
        print(f"    Min Time Loss: {min_time_loss:.2f} seconds")
        print(f"    Number of Vehicles: {vehicle_count}")
    else:
        print(f"  {approach.capitalize()} Approach: No data")
