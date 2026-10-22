"""JLCPCB placement file (CPL) from the board, with JLC's orientation conventions applied.

JLC places each part by its own (EasyEDA) model: origin at the part centre, its own zero rotation. Footprints drawn
from EasyEDA (lib/jlc) already match; KiCad library footprints may not. FIX lists the corrections, each checked in
JLC's placement viewer: (extra rotation in degrees, place at the pad centre instead of the footprint origin).
Only fitted parts named in the BOM are written.
usage: $KPY -I tools/cpl.py <board> <bom.csv> <out.csv>
"""
import csv, re, sys, pcbnew

FIX = [
    (r"^SOT-223", 180, False),                       # U2: model tab on the pin side otherwise
    (r"^SOT-23$", 180, False),                       # Q101..Q104, Q201: pin 1 on the wrong side otherwise
    (r"^SOT-23-6$", -90, False),                     # U3: JLC's model has its leads along the other axis
    (r"^PinHeader_1x\d+_P2\.54mm_Vertical", 90, True),   # KiCad origin is pin 1 and pins run along y; JLC: centre, along x
    (r"^USB_C_Receptacle_HRO_TYPE-C-31-M-12", 0, True),  # J1: KiCad origin 1.46 mm off the pad centre JLC uses
]

B, BOM, OUT = sys.argv[1:]
fitted = {r.strip() for row in csv.DictReader(open(BOM)) for r in row["Designator"].split(",")}
rows, seen = [], set()
for f in pcbnew.LoadBoard(B).Footprints():
    ref = f.GetReference()
    if ref not in fitted: continue
    seen.add(ref)
    name = f.GetFPID().GetLibItemName().wx_str()
    rot, centre = f.GetOrientationDegrees(), False
    for pat, d, c in FIX:
        if re.search(pat, name): rot, centre = rot + d, c; break
    if centre:
        bb = pcbnew.BOX2I()
        for p in f.Pads(): bb.Merge(p.GetBoundingBox())
        pos = bb.GetCenter()
    else:
        pos = f.GetPosition()
    rot = (rot + 180) % 360 - 180
    rows.append([ref, f"{pos.x / 1e6:.4f}mm", f"{-pos.y / 1e6:.4f}mm", "Top" if f.GetLayer() == pcbnew.F_Cu else "Bottom", f"{rot:g}"])
rows.sort(key=lambda r: (re.sub(r"\d", "", r[0]), int(re.sub(r"\D", "", r[0]) or 0)))
with open(OUT, "w", newline="") as fh:
    w = csv.writer(fh); w.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"]); w.writerows(rows)
miss = sorted(fitted - seen)
print(f"CPL: {len(rows)} placements" + (f", NOT ON BOARD: {miss}" if miss else ", all BOM designators placed"))
sys.exit(1 if miss else 0)
