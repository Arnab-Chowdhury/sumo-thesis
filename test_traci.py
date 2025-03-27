import traci

# Start the SUMO simulation in headless mode (no GUI)
sumo_cmd = ["sumo", "-c", "osm.sumocfg"]
traci.start(sumo_cmd)

# Get the list of traffic light IDs
tls_ids = traci.trafficlight.getIDList()
print("Traffic Lights:", tls_ids)

# Run the simulation for a few steps to collect data
for step in range(10):
    traci.simulationStep()  # Run the simulation for one step
    print(f"Simulation Step: {step + 1}")
    
    # For each traffic light, get the current phase (signal state)
    for tls_id in tls_ids:
        current_phase = traci.trafficlight.getPhase(tls_id)
        print(f"Traffic Light {tls_id}: Current Phase = {current_phase}")

# Close the connection after running the simulation steps
traci.close()
print("TraCI closed.")
