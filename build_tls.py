"""Generate a 4-phase split-phasing TLS program for junction J0 (Bijoy Sarani).

Phases: SOUTH -> yellow -> EAST -> yellow -> NORTH -> yellow -> WEST -> yellow.
Each green phase serves ALL movements of one approach (split phasing = the
"one player moves at a time" formulation of the 4-player game).

Within a phase, links that merge into a lane already claimed by a
lower-indexed active link are marked 'g' (yield) instead of 'G' to avoid
unsafe double-priority greens.
"""
import re

NET = "bijoy_v3.net.xml"
DEAD = set()

APPROACHES = ["S", "E", "N", "W"]
APPROACH_EDGE = {
    "S": "142049043#7",
    "E": "1126771720#0",
    "N": "24375730#8",
    "W": "15491645#1.359",
}
YELLOW = 5  # s, per interphase


def _link_table():
    """linkIndex -> (approach, toLane) from the net file."""
    txt = open(NET).read()
    pat = re.compile(
        r'<connection from="([^"]+)" to="([^"]+)" fromLane="(\d+)" toLane="(\d+)"'
        r'[^>]*?tl="J0" linkIndex="(\d+)"'
    )
    edge2app = {v: k for k, v in APPROACH_EDGE.items()}
    table = {}
    for frm, to, _fl, tl, idx in pat.findall(txt):
        table[int(idx)] = (edge2app[frm], f"{to}_{tl}")
    return table


LINKS = _link_table()


def phase_state(active):
    """43-char state string with `active` approach green, conflict-aware."""
    chars = ["r"] * (max(LINKS) + 1)
    claimed = set()
    for idx in sorted(LINKS):
        app, tolane = LINKS[idx]
        if app != active:
            continue
        if tolane in claimed:
            chars[idx] = "g"          # merge conflict within the approach
        else:
            chars[idx] = "G"
            claimed.add(tolane)
    return "".join(chars)


def yellow_state(active):
    green = phase_state(active)
    return "".join("y" if c in "Gg" else "r" for c in green)


def tls_xml(greens, program_id="split"):
    """greens: dict approach -> green seconds (ints)."""
    lines = [f'    <tlLogic id="J0" type="static" programID="{program_id}" offset="0">']
    for app in APPROACHES:
        lines.append(
            f'        <phase duration="{int(round(greens[app]))}" state="{phase_state(app)}"/>'
        )
        lines.append(
            f'        <phase duration="{YELLOW}" state="{yellow_state(app)}"/>'
        )
    lines.append("    </tlLogic>")
    return "\n".join(lines)


def write_additional(greens, path, program_id="split"):
    with open(path, "w") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n<additional>\n')
        f.write(tls_xml(greens, program_id))
        f.write("\n</additional>\n")


if __name__ == "__main__":
    # sanity print: equal split, 100s green budget over cycle 120
    eq = {a: 25 for a in APPROACHES}
    print(tls_xml(eq))
    per_app = {}
    for i, (a, _) in LINKS.items():
        per_app.setdefault(a, []).append(i)
    for a in APPROACHES:
        print(a, sorted(per_app[a]))
    assert set(LINKS) == set(range(max(LINKS)+1)), "link coverage mismatch"
    print("coverage OK:", len(LINKS), "links")
