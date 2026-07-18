"""Demand files from the 7-day dataset.
usage: gen_week.py <hour> <spec>   spec: 'mean4' (Sun-Wed mean) or a day like '16-2-2023'
writes rou_<spec>_h<hour>.xml"""
import pickle, sys
from gen_demand import FROM_TO, VIA, MOTORIZED

def generate_week(hour, spec):
    week = pickle.load(open("od_week.pkl","rb"))
    if spec == "mean4":
        days = ["12-2-2023","13-2-2023","14-2-2023","15-2-2023"]
        get = lambda mv: sum(week[d][(mv[0],mv[2])].loc[hour] for d in days)/len(days)
    else:
        get = lambda mv: week[spec][(mv[0],mv[2])].loc[hour]
    path = f"rou_{spec}_h{hour}.xml"
    lines = ['<?xml version="1.0" encoding="UTF-8"?>','<routes>']
    tot = 0.0
    for mv,(frm,to) in sorted(FROM_TO.items()):
        row = get(mv); via = f' via="{VIA[mv]}"' if mv in VIA else ""
        for cls in MOTORIZED:
            r = float(row[cls])
            if r <= 0: continue
            tot += r
            lines.append(f'    <flow id="{mv}.{cls}" type="{cls}" begin="0" end="3600" '
                         f'from="{frm}" to="{to}"{via} perHour="{r:.2f}" '
                         f'departLane="best" departSpeed="avg"/>')
    lines += ["</routes>",""]
    open(path,"w").write("\n".join(lines))
    print(f"{path}: {tot:.0f} veh/h")
    return path

if __name__ == "__main__":
    generate_week(int(sys.argv[1]), sys.argv[2])
