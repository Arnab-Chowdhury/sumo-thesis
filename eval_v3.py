"""Held-out Thursday evaluation on the corrected model (v3).
Arms: p0 (as-built 39/39 c90), equal4, EGT-4, EGT-2 c75, EGT-2 c90.
Plans read from trained checkpoints. Checkpointed; rerun until DONE."""
import json, os, time
from egt import run_sim, APPROACHES, shares_to_greens
from egt2 import run2, to_greens_c

def plan4(ck):
    h = json.load(open(ck))["hist"][-4:]
    sh = {a: sum(g["shares"][a] for g in h)/len(h) for a in APPROACHES}
    return shares_to_greens(sh)

def plan2(ck, cycle):
    h = json.load(open(ck))["hist"][-3:]
    x = sum(g["x"] for g in h)/len(h)
    return to_greens_c(x, cycle)

P4 = {h: plan4(f"ck4_v3_h{h}.json") for h in ("6","13","18")}
P2_75 = {h: plan2(f"ck2_v3_h{h}_c75.json", 75) for h in ("6","13","18")}
P2_90 = {h: plan2(f"ck2_v3_h{h}_c90.json", 90) for h in ("6","13","18")}

JOBS = []
for h in ("6","13","18"):
    for seed in (101,102,103):
        for c in ("p0","equal4","egt4","egt2c75","egt2c90"):
            JOBS.append(("16-2-2023", h, c, seed))
for seed in (101,102):                    # Friday transfer @ evening peak
    for c in ("p0","egt2c75","egt4"):
        JOBS.append(("17-2-2023", "18", c, seed))

CK = "ckeval_v3.json"
res = json.load(open(CK)) if os.path.exists(CK) else {}
t0 = time.time()
for day, h, c, seed in JOBS:
    k = f"{day}_h{h}_{c}_{seed}"
    if k in res: continue
    if time.time()-t0 > 250: print("RESUME"); raise SystemExit
    route = f"rou_{day}_h{h}.xml"
    if c == "p0":        r = run2(39, 39, route, seed, k)
    elif c == "equal4":  r = run_sim({a:25 for a in APPROACHES}, route, seed, k)
    elif c == "egt4":    r = run_sim(P4[h], route, seed, k)
    elif c == "egt2c75": r = run2(*P2_75[h], route, seed, k)
    else:                r = run2(*P2_90[h], route, seed, k)
    res[k] = {"all": r["ALL"]["eff_delay"], "n": r["ALL"]["n"], "miss": r["ALL"]["missing"]}
    json.dump(res, open(CK,"w"))
    print(f"{k}: {r['ALL']['eff_delay']:.1f}s n={r['ALL']['n']}")
print("DONE")
print("plans:", json.dumps({"P4": P4, "P2_75": P2_75, "P2_90": P2_90}))
