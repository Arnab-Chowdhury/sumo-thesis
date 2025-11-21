# **Evolutionary Game-Theoretic Signal Timing Optimization for Bijoy Sarani Intersection (SUMO Simulation)**

This repository contains the code, data, and workflow for my undergraduate thesis on **adaptive traffic signal optimization using Evolutionary Game Theory (EGT)**. The study focuses on the **Bijoy Sarani intersection** in Dhaka and evaluates the performance of an EGT-based controller using the **SUMO** microscopic traffic simulator.

---

## 🚦 **Project Overview**

Fixed-time traffic signals fail to cope with Dhaka’s highly fluctuating traffic patterns. This work implements an **Evolutionary Game-Theoretic (EGT) signal controller**, where each approach of the intersection behaves like a “player” competing for green time.

A cycle-by-cycle adaptive controller is developed using **replicator dynamics**, where approaches with higher delay gain more green time in the next cycle.

The method is tested on 7 days of real-world classified traffic data (recorded in 15-minute intervals), and its performance is compared against a typical **fixed 30-second-per-phase** baseline.

---

## 🧠 **Key Contributions**

* Built a full SUMO model of the **Bijoy Sarani intersection** using OSM data + NETEDIT refinement
* Generated realistic multi-modal traffic demand from **7 days of observed counts**
* Implemented an **adaptive signal controller** based on Evolutionary Game Theory
* Created Python scripts to:

  * Extract delay values from SUMO outputs
  * Compute replicator-dynamic green splits
  * Update SUMO signal plans at each cycle
* Performed comparative evaluation between **fixed-time vs. EGT** control
* Demonstrated measurable **reductions in mean delay**, especially during imbalanced peak periods

---


## ⚙️ **Methodology (Short Version)**

1. **Network Creation**

   * Generated via `osmWebWizard.py`
   * Refined in NETEDIT (junction shape, connections, lanes)

2. **Demand Modeling**

   * 15-minute interval classified counts
   * vTypes: cars, motorcycles, autos, buses, trucks
   * SUMO **flows** over each movement

3. **Baseline Controller**

   * 4-phase fixed-time signal
   * 30 seconds per green

4. **EGT Controller**

   * For each cycle:

     1. Run simulation for one cycle
     2. Extract approach delays
     3. Convert delay → payoff
     4. Apply replicator dynamics
     5. Update green splits
     6. Continue to next cycle

5. **Performance Evaluation**

   * Mean delay
   * Queue lengths
   * Visual inspection in SUMO GUI

---

## 📊 **Results (Summary)**

* EGT reduced **mean delay** compared to fixed-time control
* Performed especially well during **uneven directional flows**
* Adapted automatically to shifting traffic conditions
* Required no calibration, saturation flow inputs, or offline learning

Full results are in `results/` and the individual evaluation notebooks.

---

## 🧪 **How to Run the Project**

### **1. Install SUMO**

Linux:

```bash
sudo apt install sumo sumo-tools sumo-doc
```

Windows:
Download from: [https://sumo.dlr.de/docs/Downloads.html](https://sumo.dlr.de/docs/Downloads.html)

---

### **2. Clone the Repository**

```bash
git clone https://github.com/arnabz/traffic-egt-bijoy-sarani.git
cd traffic-egt-bijoy-sarani
```

### **3. Run the Baseline Simulation**

```bash
sumo-gui -c network/osm.sumocfg
```

### **4. Run the EGT Controller**

```bash
python controller/egt_so4.py
```
