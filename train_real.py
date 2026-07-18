"""Checkpointed EGT training on real h18 demand. Rerun until 'DONE'."""
import json, os, sys, time
from egt import APPROACHES, run_sim, shares_to_greens, replicator_step, fitness
from egt2 import run2, to_greens_c, PAIRS, pair_delay

import os
ROUTE = os.environ.get("ROUTE", "rou_real_h18.xml")
SEEDS = [42, 43]

def train4(gens=8, ckpt=os.environ.get("CKPT", "ck4_real.json")):
    st = json.load(open(ckpt)) if os.path.exists(ckpt) else \
         {"x": {a: 0.25 for a in APPROACHES}, "dbar": None, "hist": []}
    t0 = time.time()
    while len(st["hist"]) < gens and time.time() - t0 < 300:
        gen = len(st["hist"]); greens = shares_to_greens(st["x"])
        runs = [run_sim(greens, ROUTE, s, f"r4g{gen}s{s}") for s in SEEDS]
        d = {a: sum(r[a]["eff_delay"] for r in runs)/len(runs) for a in APPROACHES}
        allv = sum(r["ALL"]["eff_delay"] for r in runs)/len(runs)
        st["dbar"] = d if st["dbar"] is None else \
                     {a: 0.5*st["dbar"][a] + 0.5*d[a] for a in APPROACHES}
        f = {a: fitness(st["dbar"][a]) for a in APPROACHES}
        st["hist"].append({"gen": gen, "greens": greens, "shares": dict(st["x"]),
                           "all": round(allv, 2)})
        print(f"gen {gen} S/E/N/W={greens['S']}/{greens['E']}/{greens['N']}/{greens['W']} "
              f"d={'/'.join(f'{d[a]:.0f}' for a in APPROACHES)} ALL={allv:.1f}")
        st["x"] = replicator_step(st["x"], f)
        json.dump(st, open(ckpt, "w"))
    print("DONE" if len(st["hist"]) >= gens else "RESUME")

def train2(gens=6, cycle=int(os.environ.get("CYCLE", 75)), ckpt=os.environ.get("CKPT", "ck2_real.json")):
    st = json.load(open(ckpt)) if os.path.exists(ckpt) else \
         {"x": 0.44, "dbar": None, "hist": []}
    t0 = time.time()
    while len(st["hist"]) < gens and time.time() - t0 < 300:
        gen = len(st["hist"]); g_ns, g_ew = to_greens_c(st["x"], cycle)
        runs = [run2(g_ns, g_ew, ROUTE, s, f"r2g{gen}s{s}") for s in SEEDS]
        d = {p: sum(pair_delay(r, p) for r in runs)/len(runs) for p in PAIRS}
        allv = sum(r["ALL"]["eff_delay"] for r in runs)/len(runs)
        st["dbar"] = d if st["dbar"] is None else \
                     {p: 0.5*st["dbar"][p] + 0.5*d[p] for p in PAIRS}
        f = {p: st["dbar"][p] + 1.0 for p in PAIRS}
        st["hist"].append({"gen": gen, "g_ns": g_ns, "g_ew": g_ew,
                           "x": round(st["x"], 4), "all": round(allv, 2)})
        print(f"gen {gen} NS/EW={g_ns}/{g_ew} dNS/dEW={d['NS']:.0f}/{d['EW']:.0f} ALL={allv:.1f}")
        fbar = st["x"]*f["NS"] + (1-st["x"])*f["EW"]
        y = st["x"]*(f["NS"]/fbar)**0.5; z = (1-st["x"])*(f["EW"]/fbar)**0.5
        st["x"] = y/(y+z)
        json.dump(st, open(ckpt, "w"))
    print("DONE" if len(st["hist"]) >= gens else "RESUME")

if __name__ == "__main__":
    train4() if sys.argv[1] == "4" else train2()
