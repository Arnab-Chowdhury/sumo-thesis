import traci
import os
import random
import gzip
from xml.etree import ElementTree as ET

# SUMO Configuration
sumo_config = {
    "sumo_bin": "C:/Program Files (x86)/Eclipse/Sumo/bin/sumo.exe",  # Headless
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
mutation_rate = 0.1
num_generations = 10

# Define approaches globally
approaches = {
    "west": ["15491645#0"],
    "south": ["142049043#0"],
    "north": ["141821921#1"],
    "east": ["143870423"]
}

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
    """Run SUMO simulation and return mean delays"""
    traci.start([
        sumo_config["sumo_bin"],
        "-c", sumo_config["sumocfg"],
        "--net-file", "osm_updated.net.xml.gz",
        "--tripinfo-output", "tripinfo.xml"
    ])
    
    # Run simulation for the full duration
    for _ in range(sumo_config["simulation_steps"]):
        traci.simulationStep()
    
    traci.close()
    
    # Parse tripinfo.xml
    tree = ET.parse("tripinfo.xml")
    root = tree.getroot()
    approach_data = {key: [] for key in approaches.keys()}

    for trip in root.findall('tripinfo'):
        time_loss = float(trip.get('timeLoss', 0))
        depart_lane = trip.get('departLane', '')
        start_edge = depart_lane.split('_')[0]

        for approach, edges in approaches.items():
            if start_edge in edges:
                approach_data[approach].append(time_loss)
                break

    # Calculate mean delays
    mean_delays = {}
    for approach, delays in approach_data.items():
        mean_delays[approach] = sum(delays) / len(delays) if delays else 0
    
    return mean_delays

# Evolutionary loop
for generation in range(num_generations):
    print(f"\n=== Generation {generation + 1} ===")
    
    # 1. Update green durations in .net.xml
    update_traffic_light_phases()
    
    # 2. Run simulation and get delays
    mean_delays = run_simulation()
    print("Current Mean Delays:", mean_delays)
    
    # 3. Calculate payoffs (inverse of delay)
    payoffs = {approach: 1 / (mean_delays[approach] + 1e-6) for approach in strategies}
    total_payoff = sum(payoffs.values())
    
    # 4. Update strategies (replicator dynamics)
    for approach in strategies:
        if total_payoff > 0:
            # Increase green time proportionally to payoff
            strategies[approach] += int(2 * (payoffs[approach] / total_payoff))
        
        # Mutation: Randomly adjust green time
        if random.random() < mutation_rate:
            strategies[approach] += random.choice([-2, 0, 2])
        
        # Ensure green time stays within 10-60 seconds
        strategies[approach] = max(10, min(60, strategies[approach]))
    
    print("Updated Strategies:", strategies)