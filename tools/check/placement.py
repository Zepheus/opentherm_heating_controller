"""Quick placement check: courtyard overlaps, courtyards outside the outline, pads of neighbouring parts closer than
0.25 mm. Run after tools/layout/place.py, before routing.
usage: <kicad python> -I tools/check/placement.py <board>
"""
import sys, pcbnew
b = pcbnew.LoadBoard(sys.argv[1]); mm = lambda v: v / 1e6
eb = b.GetBoardEdgesBoundingBox(); boxes, pads = [], []
for f in b.Footprints():
    c = f.GetCourtyard(pcbnew.F_CrtYd); bb = c.BBox() if c.OutlineCount() else f.GetBoundingBox(False, False); boxes.append((f.GetReference(), bb))
    for p in f.Pads():
        pb = p.GetBoundingBox(); pb.Inflate(pcbnew.FromMM(0.25)); pads.append((f.GetReference(), p.GetNetCode(), pb))
ov = [(a[0], c[0]) for i, a in enumerate(boxes) for c in boxes[i + 1:] if a[1].Intersects(c[1])]
out = [r for r, bb in boxes if r != "J1" and (bb.GetLeft() < eb.GetLeft() + pcbnew.FromMM(0.3) or bb.GetTop() < eb.GetTop() + pcbnew.FromMM(0.3) or bb.GetRight() > eb.GetRight() - pcbnew.FromMM(0.3) or bb.GetBottom() > eb.GetBottom() - pcbnew.FromMM(0.3))]
clash = sorted(set((a[0], c[0]) for i, a in enumerate(pads) for c in pads[i + 1:] if a[0] != c[0] and (a[1] != c[1] or a[1] == 0) and a[2].Intersects(c[2])))
print("courtyard overlaps:", ov or "none"); print("outside outline:", out or "none"); print("pad clashes:", clash or "none")
sys.exit(1 if ov or out or clash else 0)
