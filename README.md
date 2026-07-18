# Evolutionary Game-Theoretic Traffic Signal Optimisation — Bijoy Sarani, Dhaka

SUMO microsimulation study of evolutionary game theory (EGT) signal timing at the
Bijoy Sarani intersection, Dhaka, with a site-specific saturation-flow calibration
for heterogeneous, non-lane-based traffic and a seven-day classified
turning-movement survey (12–18 Feb 2023).

**Headline result (held-out Thursday, 3 seeds, effective delay s/veh):**

| Hour | As-built (39/39, c90) | EGT-2 (c75) | EGT-4 (c120) |
|------|----------------------:|------------:|-------------:|
| 06:00 | **13.5 ± 0.1** | 13.6 ± 0.4 | 16.9 ± 0.3 |
| 13:00 | **16.8 ± 0.2** | 16.8 ± 1.3 | 19.8 ± 1.8 |
| 18:00 | 39.9 ± 4.7 | 39.4 ± 7.2 | **25.6 ± 6.1 (−36%)** |

With field-realistic capacity the junction is undersaturated at all hours, so the
binding design choice is **phase structure matched to demand asymmetry**, not
cycle length: balanced hours are already served near-optimally by a well-set
fixed plan (EGT converges to it), while the asymmetric evening peak is won by
split-phase EGT-4, which reallocates green to the heavily loaded Jahangir Gate
approach (evolved split 10/10/65/15 for S/E/N/W).

## Requirements

```bash
pip install eclipse-sumo sumolib
```

Python ≥ 3.10. Everything runs headless; `sumo-gui` (same package) opens the
scenario visually. Tested with SUMO 1.27.1.

## Quickstart

Open the scenario in the GUI (evening-peak demand, calibrated fleet):

```bash
sumo-gui -c bijoy.sumocfg
```

Reproduce the headline peak comparison (two ~20 s simulations):

```python
from egt2 import run2          # paired 2-phase runner (as-built = 39/39)
from egt import run_sim        # split 4-phase runner

r = run2(39, 39, "rou_16-2-2023_h18.xml", 101, "p0")
print(r["ALL"]["eff_delay"])   # -> 43.1  (as-built, peak, seed 101)

r = run_sim({"S":10,"E":10,"N":65,"W":15}, "rou_16-2-2023_h18.xml", 101, "egt4")
print(r["ALL"]["eff_delay"])   # -> 21.4  (evolved EGT-4 plan)
```

Reproduce the full held-out evaluation matrix (3 hours × 3 seeds × 5
controllers + Friday transfer; ~15 min, checkpointed — rerun until `DONE`):

```bash
python3 eval_v3.py
```

Results accumulate in `ckeval_v3.json` (the shipped copy contains the paper's
numbers).

## Retraining from scratch

```bash
# EGT-4 (split phase, cycle 120), e.g. evening peak:
ROUTE=rou_mean4_h18.xml CKPT=ck4_v3_h18.json python3 train_real.py 4

# EGT-2 (paired phase) at a chosen cycle:
ROUTE=rou_mean4_h18.xml CYCLE=75 CKPT=ck2_v3_h18_c75.json python3 train_real.py 2
```

Training is checkpointed per generation; rerun the command until it prints
`DONE`. Plans are trained on the Sun–Wed mean demand (`rou_mean4_*`) and
evaluated on held-out Thursday (`rou_16-2-2023_*`) plus a Friday transfer check
(`rou_17-2-2023_h18`).

Regenerate demand for any hour/day from the survey pickle:

```bash
python3 gen_week.py 18 16-2-2023     # -> rou_16-2-2023_h18.xml
python3 gen_week.py 6 mean4          # -> rou_mean4_h6.xml (Sun–Wed mean)
```

## File inventory

| File | Role |
|---|---|
| `bijoy_v3.net.xml` | SUMO network: joined signalised cluster `J0`, ground-truth lanes (N 4 / E 3 / S 4 / W 4), slip-lane free lefts |
| `bp.nod.xml`, `bp.edg.xml`, `bp.con.xml`, `bp.typ.xml` | plain-XML sources — rebuild the net with `netconvert --node-files bp.nod.xml --edge-files bp.edg.xml --connection-files bp.con.xml --type-files bp.typ.xml --lefthand --tls.default-type static -o bijoy_v3.net.xml` |
| `vtypes_cal.add.xml` | calibrated 10-class Dhaka fleet: τ=0.9 s, minGap 1.2 m, minGapLat 0.3 m (use with `--lateral-resolution 0.8`; ≈2,750 veh/h/lane) |
| `od_week.pkl` | parsed 7-day survey: `{day: {(from,to): 24 h × 14-class DataFrame}}`, leg letters n/e/s/w |
| `gen_week.py`, `gen_demand.py` | demand generators (per-day/hour flows; slip-lane lefts hard-routed) |
| `rou_mean4_h{6,13,18}.xml` | training demand (Sun–Wed mean) |
| `rou_16-2-2023_h{6,13,18}.xml`, `rou_17-2-2023_h18.xml` | held-out Thursday + Friday transfer demand |
| `egt.py` | split-phase (4-player) runner + replicator machinery |
| `egt2.py` | paired-phase (2-player) runner; as-built = `run2(39, 39, ...)` |
| `build_tls.py` | 4-phase TLS program generator (net-derived link groups) |
| `train_real.py` | checkpointed EGT training (damped replicator, α=β=0.5) |
| `eval_v3.py` | held-out evaluation matrix |
| `ga_bench.py` | budget-matched (3+3) evolution-strategy benchmark |
| `ck4_v3_h*.json`, `ck2_v3_h*_c*.json` | trained checkpoints (all hours/cycles) |
| `ckeval_v3.json` | full evaluation results behind the paper's tables |
| `bijoy.sumocfg` | ready-to-open SUMO configuration (peak hour) |

## Method in one paragraph

Approaches are players holding shares of a fixed green budget. After each
multi-seed simulation, per-approach delay is EMA-smoothed (β=0.5) and used as
fitness (pressure = delay + 1); shares evolve by damped discrete replicator
dynamics (exponent α=0.5), projected to a minimum green and integer seconds.
The fixed point equalises pressure across approaches — an ESS-like,
equisaturated allocation. Effective delay charges 600 s per expected-but-unserved
vehicle so a plan cannot game the mean by starving an approach (inert here:
demand clears in full at every hour).

## Notes

- The network is left-hand drive; all four left turns run on channelised slip
  lanes that bypass the signal and are hard-routed in the demand.
- `od_week_orig.pkl` is the survey pickle under the original (pre-correction)
  leg lexicon, kept for provenance; all experiments use `od_week.pkl`.
- Simulations write `tripinfo.xml` / `ti_*.xml` locally; these are regenerable
  and git-ignored.
