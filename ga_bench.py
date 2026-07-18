"""Same-budget black-box benchmark: (3+3) evolution strategy over (cycle, x).
Budget = 12 sims = 6 candidates x 2 seeds, identical to EGT-2 training."""
import json, os, random, time
from egt2 import run2, to_greens_c

import os
ROUTE = os.environ.get("ROUTE", "rou_real_h13.xml")
SEEDS, CK = [42, 43], os.environ.get("CK", "ckga_h13.json")

def evaluate(cyc, x, tag):
    g_ns, g_ew = to_greens_c(x, cyc)
    vals = [run2(g_ns, g_ew, ROUTE, s, f"ga_{tag}_s{s}")["ALL"]["eff_delay"] for s in SEEDS]
    return sum(vals)/len(vals), g_ns, g_ew

st = json.load(open(CK)) if os.path.exists(CK) else {"evals": []}
rng = random.Random(7)
# fixed candidate list: 3 random + 3 mutations of best-so-far
t0 = time.time()
while len(st["evals"]) < 6 and time.time() - t0 < 240:
    i = len(st["evals"])
    if i < 3:
        cyc, x = rng.randint(60, 110), rng.uniform(0.3, 0.7)
    else:
        best = min(st["evals"], key=lambda e: e["score"])
        cyc = max(60, min(110, int(best["cyc"] + rng.gauss(0, 10))))
        x = max(0.3, min(0.7, best["x"] + rng.gauss(0, 0.08)))
    score, g_ns, g_ew = evaluate(cyc, x, i)
    st["evals"].append({"i": i, "cyc": cyc, "x": round(x,3),
                        "g": f"{g_ns}/{g_ew}", "score": round(score,1)})
    json.dump(st, open(CK, "w"))
    print(st["evals"][-1])
best = min(st["evals"], key=lambda e: e["score"])
print(("DONE  best: " if len(st["evals"])>=6 else "RESUME  best so far: ") + str(best))
