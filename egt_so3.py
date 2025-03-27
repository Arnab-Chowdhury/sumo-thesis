import traci
import os
import random
import gzip
import numpy as np
from xml.etree import ElementTree as ET
import csv
from datetime import datetime

# SUMO Configuration
sumo_config = {
    "sumo_bin": "C:/Program Files (x86)/Eclipse/Sumo/bin/sumo.exe",
    "net_file": "osm.net.xml.gz",
    "route_file": "osm.rou.xml",
    "sumocfg": "osm.sumocfg",
    "simulation_steps": 3600
}

# EGT Parameters
strategies = {
    "west": 30,
    "south": 30,
    "north": 30,
    "east": 30
}
mutation_rate = 0.2  # Increased mutation rate
mutation_step = 5    # Larger mutation steps
num_generations = 20
approaches = {
    "west": ["15491645#0"],
    "south": ["142049043#0"],
    "north": ["141821921#1"],
    "east": ["143870423"]
}

# Initialize logging
log_file = f"optimization_log_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
with open(log_file, 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(["Generation", "Approach", "GreenTime", "MeanDelay", "MaxDelay", "MinDelay", "VehicleCount"])

def log_results(generation, approach_data):
    """Log results to CSV file"""
    with open(log_file, 'a', newline='') as f:
        writer = csv.writer(f)
        for approach, data in approach_data.items():
            writer.writerow([
                generation,
                approach,
                strategies[approach],
                data["mean"],
                data["max"],
                data["min"],
                data["count"]
            ])

def update_traffic_light_phases():
    """Update green durations in osm.net.xml.gz"""
    with gzip.open("osm.net.xml.gz", "rt", encoding="utf-8") as f:
        tree = ET.parse(f)
        root = tree.getroot()

    for tl_logic in root.findall(".//tlLogic"):
        if tl_logic.get("id") == "J0":
            phases = tl_logic.findall("phase")
            phases[0].set("duration", str(strategies["west"]))
            phases[2].set("duration", str(strategies["south"]))
            phases[4].set("duration", str(strategies["north"]))
            phases[6].set("duration", str(strategies["east"]))

    with gzip.open("osm_updated.net.xml.gz", "wb") as f:
        tree.write(f, encoding="utf-8", xml_declaration=True)

def run_simulation():
    """Run SUMO simulation and return delay statistics"""
    traci.start([
        sumo_config["sumo_bin"],
        "-c", sumo_config["sumocfg"],
        "--net-file", "osm_updated.net.xml.gz",
        "--tripinfo-output", "tripinfo.xml"
    ])
    
    for _ in range(sumo_config["simulation_steps"]):
        traci.simulationStep()
    
    traci.close()
    
    # Parse tripinfo.xml
    tree = ET.parse("tripinfo.xml")
    root = tree.getroot()
    approach_data = {key: {"delays": [], "count": 0} for key in approaches.keys()}

    for trip in root.findall('tripinfo'):
        time_loss = float(trip.get('timeLoss', 0))
        depart_lane = trip.get('departLane', '')
        start_edge = depart_lane.split('_')[0]

        for approach, edges in approaches.items():
            if start_edge in edges:
                approach_data[approach]["delays"].append(time_loss)
                approach_data[approach]["count"] += 1
                break

    # Calculate statistics
    stats = {}
    for approach, data in approach_data.items():
        if data["count"] > 0:
            stats[approach] = {
                "mean": np.mean(data["delays"]),
                "max": np.max(data["delays"]),
                "min": np.min(data["delays"]),
                "count": data["count"]
            }
        else:
            stats[approach] = {
                "mean": 0,
                "max": 0,
                "min": 0,
                "count": 0
            }
    
    return stats

# Evolutionary optimization loop
for generation in range(num_generations):
    print(f"\n=== Generation {generation + 1}/{num_generations} ===")
    
    # 1. Update traffic light phases
    update_traffic_light_phases()
    
    # 2. Run simulation and get statistics
    stats = run_simulation()
    
    # 3. Log results
    log_results(generation + 1, stats)
    
    # 4. Calculate exponential payoffs (prioritize reducing large delays)
    payoffs = {
        approach: np.exp(-stats[approach]["mean"] / 10)  # Exponential decay payoff
        for approach in strategies
    }
    total_payoff = sum(payoffs.values())
    
    # 5. Update strategies with momentum
    print("Current Statistics:")
    for approach in strategies:
        current_stats = stats[approach]
        print(f"  {approach.upper()}: "
              f"{current_stats['mean']:.1f}s avg delay "
              f"({current_stats['count']} vehicles)")
        
        # Calculate strategy adjustment
        if total_payoff > 1e-6:  # Avoid division by zero
            payoff_ratio = payoffs[approach] / total_payoff
            adjustment = int(8 * payoff_ratio)  # Aggressive scaling
            strategies[approach] += adjustment
        
        # Apply mutation
        if random.random() < mutation_rate:
            strategies[approach] += random.choice([-mutation_step, mutation_step])
        
        # Clamp values between 10-60 seconds
        strategies[approach] = max(10, min(60, strategies[approach]))
    
    print("Updated Strategies:", strategies)

print("\nOptimization complete! Results saved to", log_file)