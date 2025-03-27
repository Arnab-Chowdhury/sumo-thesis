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
mutation_rate = 0.1
mutation_step = 3
num_generations = 20
max_phases = 60
min_phases = 10

# VALIDATED APPROACHES - UPDATE THESE BASED ON YOUR NETWORK
approaches = {
    "west": {"edges": ["15491645#0"]},
    "south": {"edges": ["142049043#0"]},
    "north": {"edges": ["141821921#1"]},
    "east": {"edges": ["143870423"]}
}

# Payoff Weights
weights = {
    "delay": 0.5,
    "throughput": 0.3,
    "queue": 0.2
}

max_metrics = {
    "delay": 100,
    "throughput": 1000,
    "queue": 20
}

# Logging setup
log_file = f"optimization_v3_log_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"

def init_log():
    with open(log_file, 'w', newline='') as f:
        writer = csv.writer(f)
        header = ["Generation", "Approach", "GreenTime"]
        header += ["MeanDelay", "MaxDelay", "Throughput", "MaxQueue"]
        header += ["Payoff", "StrategyChange"]
        writer.writerow(header)

def log_results(generation, stats, payoffs, adjustments):
    with open(log_file, 'a', newline='') as f:
        writer = csv.writer(f)
        for approach in strategies:
            data = stats[approach]
            writer.writerow([
                generation,
                approach,
                strategies[approach],
                data["mean_delay"],
                data["max_delay"],
                data["throughput"],
                data["max_queue"],
                payoffs[approach],
                adjustments.get(approach, 0)
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

def get_valid_lanes():
    """Get all valid lane IDs dynamically"""
    return set(traci.lane.getIDList())  # Corrected method

def get_approach_metrics(valid_lanes):
    """Collect metrics with lane validation"""
    metrics = {approach: {
        "delay": [],
        "throughput": 0,
        "queues": []
    } for approach in approaches}

    # Vehicle data collection
    for veh_id in traci.vehicle.getIDList():
        try:
            lane = traci.vehicle.getLaneID(veh_id)
            if lane not in valid_lanes:
                continue
            # Find approach using edge prefix matching
            edge = lane.split('_')[0]  # Extract edge from lane ID (e.g., "143870423_0" → "143870423")
            approach = next(
                (a for a, data in approaches.items() if edge in data["edges"]),
                None
            )
            if approach:
                metrics[approach]["delay"].append(traci.vehicle.getTimeLoss(veh_id))
        except traci.TraCIException:
            continue

    # Queue length calculation
    for approach, data in approaches.items():
        queue_sum = 0
        max_queue = 0
        # Get all lanes for the approach's edges
        for edge in data["edges"]:
            for lane in valid_lanes:
                if lane.startswith(f"{edge}_"):
                    try:
                        queue = traci.lane.getLastStepHaltingNumber(lane)
                        queue_sum += queue
                        max_queue = max(max_queue, queue)
                    except traci.TraCIException:
                        continue
        metrics[approach]["queues"].append(queue_sum)
        metrics[approach]["max_queue"] = max_queue

    return metrics

def run_simulation():
    """Run simulation with lane validation"""
    traci.start([
        sumo_config["sumo_bin"],
        "-c", sumo_config["sumocfg"],
        "--net-file", "osm_updated.net.xml.gz",
        "--tripinfo-output", "tripinfo.xml"
    ])
    
    # Get valid lanes once at start
    valid_lanes = get_valid_lanes()
    
    metrics = {approach: {
        "delay": [],
        "throughput": 0,
        "queues": [],
        "max_queue": 0
    } for approach in approaches}

    for _ in range(sumo_config["simulation_steps"]):
        traci.simulationStep()
        current_metrics = get_approach_metrics(valid_lanes)
        
        for approach in approaches:
            metrics[approach]["delay"].extend(current_metrics[approach]["delay"])
            metrics[approach]["queues"].append(current_metrics[approach]["max_queue"])
            metrics[approach]["max_queue"] = max(
                metrics[approach]["max_queue"],
                current_metrics[approach]["max_queue"]
            )

    # Throughput calculation
    tree = ET.parse("tripinfo.xml")
    root = tree.getroot()
    for trip in root.findall('tripinfo'):
        try:
            lane = trip.get("departLane", "")
            if lane not in valid_lanes:
                continue
            approach = next(
                (a for a, data in approaches.items() if lane in data["lanes"]),
                None
            )
            if approach:
                metrics[approach]["throughput"] += 1
        except Exception:
            continue

    traci.close()

    # Process metrics
    stats = {}
    for approach in approaches:
        delays = metrics[approach]["delay"]
        queues = metrics[approach]["queues"]
        
        stats[approach] = {
            "mean_delay": np.mean(delays) if delays else 0,
            "max_delay": np.max(delays) if delays else 0,
            "throughput": metrics[approach]["throughput"],
            "mean_queue": np.mean(queues) if queues else 0,
            "max_queue": metrics[approach]["max_queue"]
        }
        
        max_metrics["delay"] = max(max_metrics["delay"], stats[approach]["max_delay"])
        max_metrics["throughput"] = max(max_metrics["throughput"], stats[approach]["throughput"])
        max_metrics["queue"] = max(max_metrics["queue"], stats[approach]["max_queue"])

    return stats

# Rest of the code remains the same from previous version for:
# - calculate_payoffs()
# - evolve_strategies()
# - main optimization loop

# [Main execution code remains identical to previous version]
# [Only the metric collection and lane validation changed]

# Initialize and run
init_log()
print("=== Initial Baseline ===")
update_traffic_light_phases()
try:
    baseline_stats = run_simulation()
    log_results(0, baseline_stats, 
               {a: 0 for a in strategies}, 
               {a: 0 for a in strategies})
except Exception as e:
    print(f"Critical error during baseline: {str(e)}")
    exit(1)

for generation in range(num_generations):
    print(f"\n=== Generation {generation+1}/{num_generations} ===")
    
    try:
        update_traffic_light_phases()
        stats = run_simulation()
        payoffs = calculate_payoffs(stats)
        adjustments = evolve_strategies(payoffs)
        log_results(generation+1, stats, payoffs, adjustments)
        
        # Display results
        print(f"{'Approach':<10} | {'GreenTime':>10} | {'MeanDelay':>10} | {'Throughput':>10} | {'MaxQueue':>10}")
        for approach in strategies:
            print(f"{approach:<10} | {strategies[approach]:>10} | "
                  f"{stats[approach]['mean_delay']:>10.1f} | "
                  f"{stats[approach]['throughput']:>10} | "
                  f"{stats[approach]['max_queue']:>10}")
    
    except Exception as e:
        print(f"Error in generation {generation+1}: {str(e)}")
        continue

print("\nOptimization complete! Results saved to", log_file)