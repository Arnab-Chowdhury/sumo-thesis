"""Generate SUMO demand from the 12-02-2023 Sunday classified turning counts.

Usage:  python3 gen_demand.py <hour> [scale]
Writes: rou_real_h<hour>[_s<scale>].xml

- One <flow> per (movement, vehicle class) with the counted perHour rate.
- Left-turn movements (e2s, s2w, w2n, n2e) are hard-routed through their
  channelized slip lanes with via="...", bypassing the signal (matching
  reality: physically separated free lefts).
- Non-motorized classes are excluded (banned on this VIP road; counts agree).
"""
import pickle
import sys

FROM_TO = {  # movement -> (from edge, to edge) [entry/exit edges of the model]
    "n2e": ("141821921#1", "566501599"),
    "n2s": ("141821921#1", "13848342#5"),
    "n2w": ("141821921#1", "1126771718#2"),
    "e2n": ("143870422#0", "141821922#6"),
    "e2s": ("143870422#0", "13848342#5"),
    "e2w": ("143870422#0", "1126771718#2"),
    "s2n": ("142049043#6", "141821922#6"),
    "s2e": ("142049043#6", "566501599"),
    "s2w": ("142049043#6", "1126771718#2"),
    "w2n": ("15491645#1", "141821922#6"),
    "w2e": ("15491645#1", "566501599"),
    "w2s": ("15491645#1", "13848342#5"),
}
# left turns bypass the signal via their slip-lane edge
VIA = {"e2s": "1126771721", "s2w": "1126771717",
       "w2n": "E3", "n2e": "1126771723"}

MOTORIZED = ["heavy_truck", "med_truck", "small_truck", "large_bus",
             "medium_bus", "micro_bus", "utility", "car", "cng", "motorcycle"]


def generate(hour, scale=1.0, path=None):
    od = pickle.load(open("od_sunday.pkl", "rb"))
    path = path or (f"rou_real_h{hour}.xml" if scale == 1.0
                    else f"rou_real_h{hour}_s{int(scale*100)}.xml")
    lines = ['<?xml version="1.0" encoding="UTF-8"?>', "<routes>"]
    total = 0.0
    for mv, (frm, to) in sorted(FROM_TO.items()):
        row = od[(mv[0], mv[2])].loc[hour]
        via = f' via="{VIA[mv]}"' if mv in VIA else ""
        for cls in MOTORIZED:
            rate = float(row[cls]) * scale
            if rate <= 0:
                continue
            total += rate
            lines.append(
                f'    <flow id="{mv}.{cls}" type="{cls}" begin="0" end="3600" '
                f'from="{frm}" to="{to}"{via} perHour="{rate:.2f}" '
                f'departLane="best" departSpeed="max"/>')
    lines += ["</routes>", ""]
    open(path, "w").write("\n".join(lines))
    print(f"wrote {path}: {sum(1 for l in lines if '<flow' in l)} flows, "
          f"{total:.0f} veh/h total (hour {hour}:00, scale {scale})")
    return path


if __name__ == "__main__":
    hour = int(sys.argv[1])
    scale = float(sys.argv[2]) if len(sys.argv) > 2 else 1.0
    generate(hour, scale)
