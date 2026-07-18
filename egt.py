"""EGT traffic-signal optimization for Bijoy Sarani (junction J0).

Four players = four approaches (S, E, N, W). Strategy of player i = its share
x_i of the fixed green budget. One generation = one full SUMO run; payoff of
player i = fitness decreasing in the effective mean delay of vehicles that
entered from approach i. Shares evolve by discrete replicator dynamics:

    x_i <- x_i * (f_i / f_bar),   f_bar = sum_j x_j f_j

then floor at a minimum-green share and renormalize (constrained simplex).
Fixed cycle length => this is a constant-sum allocation game: one approach
can only gain green by taking it from the others.
"""
import os
import subprocess
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_tls import APPROACHES, write_additional  # noqa: E402

CYCLE = 120
YELLOW_TOTAL = 4 * 5
GREEN_BUDGET = CYCLE - YELLOW_TOTAL          # 100 s
MIN_GREEN = 10                                # s
MIN_SHARE = MIN_GREEN / GREEN_BUDGET
SIM_END = 3900                                # insertion ends at 3600, then clear
PENALTY = 600.0                               # timeLoss charged per never-finished veh

ORIGIN2APP = {"s": "S", "e": "E", "n": "N", "w": "W"}


def shares_to_greens(x):
    """Continuous shares -> integer greens summing exactly to GREEN_BUDGET."""
    raw = [x[a] * GREEN_BUDGET for a in APPROACHES]
    g = [max(MIN_GREEN, int(v)) for v in raw]
    # distribute the remainder by largest fractional part
    while sum(g) < GREEN_BUDGET:
        fr = [(raw[i] - g[i], i) for i in range(4)]
        g[max(fr)[1]] += 1
    while sum(g) > GREEN_BUDGET:
        fr = [(raw[i] - g[i], i) for i in range(4) if g[i] > MIN_GREEN]
        g[min(fr)[1]] -= 1
    return dict(zip(APPROACHES, g))


def run_sim(greens, route_file, seed, tag, workdir="runs"):
    os.makedirs(workdir, exist_ok=True)
    add = os.path.join(workdir, f"tls_{tag}.add.xml")
    trip = os.path.join(workdir, f"trip_{tag}.xml")
    write_additional(greens, add)
    cmd = [
        "sumo",
        "--net-file", "bijoy_v3.net.xml",
        "--route-files", route_file,
        "--additional-files", f"vtypes_cal.add.xml,{add}",
        "--tripinfo-output", trip,
        "--begin", "0", "--end", str(SIM_END),
        "--seed", str(seed),
        "--time-to-teleport", "300",
        "--lateral-resolution", "0.8",
        "--ignore-route-errors",
        "--no-step-log", "--no-warnings",
        "--duration-log.disable",
    ]
    subprocess.run(cmd, capture_output=True, check=True)
    return parse_tripinfo(trip, route_file)


def parse_tripinfo(trip, route_file):
    root = ET.parse(trip).getroot()
    per = {a: {"n": 0, "loss": 0.0, "wait": 0.0} for a in APPROACHES}
    for ti in root.findall("tripinfo"):
        app = ORIGIN2APP[ti.get("id")[0]]
        per[app]["n"] += 1
        per[app]["loss"] += float(ti.get("timeLoss"))
        per[app]["wait"] += float(ti.get("waitingTime"))
    # expected vehicle counts per approach from the route file
    expect = {a: 0.0 for a in APPROACHES}
    for fl in ET.parse(route_file).getroot().findall("flow"):
        expect[ORIGIN2APP[fl.get("id")[0]]] += float(fl.get("perHour"))
    out = {}
    for a in APPROACHES:
        n, loss = per[a]["n"], per[a]["loss"]
        missing = max(0.0, expect[a] - n)
        out[a] = {
            "n": n,
            "missing": missing,
            "mean_loss": loss / n if n else float("inf"),
            "eff_delay": (loss + missing * PENALTY) / (n + missing) if (n + missing) else 0.0,
            "mean_wait": per[a]["wait"] / n if n else float("inf"),
        }
    tot_n = sum(per[a]["n"] for a in APPROACHES)
    tot_loss = sum(per[a]["loss"] for a in APPROACHES)
    tot_missing = sum(out[a]["missing"] for a in APPROACHES)
    out["ALL"] = {
        "n": tot_n,
        "missing": tot_missing,
        "mean_loss": tot_loss / tot_n,
        "eff_delay": (tot_loss + tot_missing * PENALTY) / (tot_n + tot_missing),
    }
    return out


def fitness(eff_delay):
    """Pressure-based fitness: green-time units replicate toward approaches
    with high delay (pressure). Equilibrium = equalized pressure."""
    return eff_delay + 1.0


ALPHA = 0.5  # damping exponent on the replicator ratio


def replicator_step(x, f):
    fbar = sum(x[a] * f[a] for a in APPROACHES)
    y = {a: x[a] * (f[a] / fbar) ** ALPHA for a in APPROACHES}
    # project onto {x >= MIN_SHARE, sum = 1}
    for _ in range(8):
        s = sum(y.values())
        y = {a: v / s for a, v in y.items()}
        low = {a for a, v in y.items() if v < MIN_SHARE}
        if not low:
            break
        free = 1.0 - MIN_SHARE * len(low)
        rest = sum(y[a] for a in APPROACHES if a not in low)
        y = {a: (MIN_SHARE if a in low else y[a] * free / rest) for a in APPROACHES}
    return y


BETA = 0.5  # EMA weight on the newest observed delay


def evolve(route_file, seed=42, generations=20, log=print, seeds=None):
    """seeds: list -> multi-seed training (payoffs averaged over seeds)."""
    train_seeds = seeds or [seed]
    x = {a: 0.25 for a in APPROACHES}
    dbar = None  # smoothed per-approach delays (payoff memory)
    history, best = [], None
    for gen in range(generations):
        greens = shares_to_greens(x)
        runs = [run_sim(greens, route_file, s, f"g{gen}_s{s}") for s in train_seeds]
        d = {a: sum(r[a]["eff_delay"] for r in runs) / len(runs) for a in APPROACHES}
        res = {a: {"eff_delay": d[a]} for a in APPROACHES}
        res["ALL"] = {"eff_delay": sum(r["ALL"]["eff_delay"] for r in runs) / len(runs)}
        dbar = d if dbar is None else {a: (1 - BETA) * dbar[a] + BETA * d[a] for a in APPROACHES}
        f = {a: fitness(dbar[a]) for a in APPROACHES}
        score = res["ALL"]["eff_delay"]
        history.append({"gen": gen, "greens": dict(greens), "shares": dict(x),
                        "per": {a: round(res[a]["eff_delay"], 1) for a in APPROACHES},
                        "all": round(score, 2)})
        if best is None or score < best["all"]:
            best = history[-1]
        log(f"gen {gen:2d} greens S/E/N/W = "
            f"{greens['S']:3d}/{greens['E']:3d}/{greens['N']:3d}/{greens['W']:3d}  "
            f"delay S/E/N/W = {res['S']['eff_delay']:6.1f}/{res['E']['eff_delay']:6.1f}/"
            f"{res['N']['eff_delay']:6.1f}/{res['W']['eff_delay']:6.1f}  ALL = {score:7.2f}")
        x = replicator_step(x, f)
    return history, best
