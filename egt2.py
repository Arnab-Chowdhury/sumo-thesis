"""2-phase EGT formulation for heavy load.

Two players: the N+S phase pair and the E+W phase pair (exactly the as-built
program's structure). The evolving quantity is the split of the 78 s green
budget within the as-built cycle (90 s, two 6 s yellows). Phase state strings
are taken verbatim from the network's program 0, so conflict handling is
identical to the existing signal -- only the durations differ.

Player payoff (pressure) = vehicle-weighted mean effective delay of the two
approaches the phase serves.
"""
import json
import os
import subprocess
import sys

from egt import APPROACHES, SIM_END, parse_tripinfo

# paired-phase states derived from the net (straight G, turn/merge g)
import sumo as _s, os as _os, sys as _sys
_sys.path.append(_os.path.join(_os.path.dirname(_s.__file__), "tools"))
import sumolib as _sl
_net = _sl.net.readNet("bijoy_v3.net.xml")
_node = next(n for n in _net.getNodes() if n.getType() == "traffic_light")
_A2E = {"S": "142049043#7", "E": "1126771720#0", "N": "24375730#8", "W": "15491645#1.359"}
_conns = [c for c in _node.getConnections() if c.getTLSID() == "J0"]
_NL = max(c.getTLLinkIndex() for c in _conns) + 1
def _pair_state(edges, yellow=False):
    chars = ["r"] * _NL; claimed = set()
    for c in sorted(_conns, key=lambda c: c.getTLLinkIndex()):
        if c.getFrom().getID() not in edges: continue
        i = c.getTLLinkIndex(); tl = (c.getTo().getID(), c.getToLane().getIndex())
        if yellow: chars[i] = "y"; continue
        if c.getDirection() in ("l","r","t","L","R") or tl in claimed: chars[i] = "g"
        else: chars[i] = "G"; claimed.add(tl)
    return "".join(chars)
_NS = [_A2E["N"], _A2E["S"]]; _EW = [_A2E["E"], _A2E["W"]]
STATE_NS, YEL_NS = _pair_state(_NS), _pair_state(_NS, True)
STATE_EW, YEL_EW = _pair_state(_EW), _pair_state(_EW, True)

CYCLE = 90
YELLOW = 6
BUDGET = CYCLE - 2 * YELLOW   # 78 s
MIN_GREEN = 15
PAIRS = {"NS": ("N", "S"), "EW": ("E", "W")}


def write_add(g_ns, g_ew, path):
    with open(path, "w") as f:
        f.write(
            '<?xml version="1.0" encoding="UTF-8"?>\n<additional>\n'
            f'    <tlLogic id="J0" type="static" programID="split2" offset="0">\n'
            f'        <phase duration="{g_ns}" state="{STATE_NS}"/>\n'
            f'        <phase duration="{YELLOW}" state="{YEL_NS}"/>\n'
            f'        <phase duration="{g_ew}" state="{STATE_EW}"/>\n'
            f'        <phase duration="{YELLOW}" state="{YEL_EW}"/>\n'
            f'    </tlLogic>\n</additional>\n')


def run2(g_ns, g_ew, route_file, seed, tag):
    os.makedirs("runs", exist_ok=True)
    add = f"runs/tls2_{tag}.add.xml"
    trip = f"runs/trip2_{tag}.xml"
    write_add(g_ns, g_ew, add)
    cmd = ["sumo", "--net-file", "bijoy_v3.net.xml",
           "--route-files", route_file, "--additional-files", f"vtypes_cal.add.xml,{add}",
           "--tripinfo-output", trip,
           "--begin", "0", "--end", str(SIM_END), "--seed", str(seed),
           "--time-to-teleport", "300", "--lateral-resolution", "0.8", "--ignore-route-errors",
           "--no-step-log", "--no-warnings", "--duration-log.disable"]
    subprocess.run(cmd, capture_output=True, check=True)
    return parse_tripinfo(trip, route_file)


def pair_delay(res, pair):
    a, b = PAIRS[pair]
    na = res[a]["n"] + res[a]["missing"]
    nb = res[b]["n"] + res[b]["missing"]
    return (res[a]["eff_delay"] * na + res[b]["eff_delay"] * nb) / (na + nb)


def to_greens(x_ns):
    g_ns = int(round(x_ns * BUDGET))
    g_ns = min(max(g_ns, MIN_GREEN), BUDGET - MIN_GREEN)
    return g_ns, BUDGET - g_ns


ALPHA, BETA = 0.5, 0.5


def to_greens_c(x_ns, cycle):
    budget = cycle - 2 * YELLOW
    g_ns = int(round(x_ns * budget))
    g_ns = min(max(g_ns, MIN_GREEN), budget - MIN_GREEN)
    return g_ns, budget - g_ns


def evolve2(route_file, seeds, generations=14, log=print, cycle=CYCLE, x0=0.5):
    x = x0  # NS share
    dbar = None
    hist, best = [], None
    for gen in range(generations):
        g_ns, g_ew = to_greens_c(x, cycle)
        runs = [run2(g_ns, g_ew, route_file, s, f"g{gen}_s{s}") for s in seeds]
        d = {p: sum(pair_delay(r, p) for r in runs) / len(runs) for p in PAIRS}
        allv = sum(r["ALL"]["eff_delay"] for r in runs) / len(runs)
        dbar = d if dbar is None else {p: (1 - BETA) * dbar[p] + BETA * d[p] for p in PAIRS}
        f = {p: dbar[p] + 1.0 for p in PAIRS}
        fbar = x * f["NS"] + (1 - x) * f["EW"]
        hist.append({"gen": gen, "g_ns": g_ns, "g_ew": g_ew, "x": round(x, 4),
                     "d_ns": round(d["NS"], 1), "d_ew": round(d["EW"], 1),
                     "all": round(allv, 2)})
        if best is None or allv < best["all"]:
            best = hist[-1]
        log(f"gen {gen:2d} NS/EW = {g_ns:2d}/{g_ew:2d}  "
            f"pairDelay NS/EW = {d['NS']:6.1f}/{d['EW']:6.1f}  ALL = {allv:7.2f}")
        y = x * (f["NS"] / fbar) ** ALPHA
        z = (1 - x) * (f["EW"] / fbar) ** ALPHA
        x = y / (y + z)
    return hist, best


if __name__ == "__main__":
    level, route = sys.argv[1], f"rou_{sys.argv[1]}.xml"
    hist, best = evolve2(route, seeds=[42, 43, 44], generations=14)
    tail = hist[-6:]
    x_mean = sum(h["x"] for h in tail) / len(tail)
    g_ns, g_ew = to_greens(x_mean)
    json.dump({"g_ns": g_ns, "g_ew": g_ew, "history": hist, "best": best},
              open(f"egt2_plan_{level}.json", "w"), indent=1)
    print(f"\nEGT-2phase plan @ {level}%: NS={g_ns} EW={g_ew} "
          f"(as-built is 39/39; best-in-training ALL={best['all']}s)")
