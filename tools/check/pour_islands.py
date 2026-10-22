"""List GND pour islands and what sits inside them, to see why DRC reports them as unconnected."""
import sys, pcbnew
b = pcbnew.LoadBoard(sys.argv[1])
gnd = b.FindNet("GND").GetNetCode()
pads = [(f.GetReference() + "." + p.GetNumber(), p.GetPosition(), p.GetLayerSet()) for f in b.Footprints() for p in f.Pads() if p.GetNetCode() == gnd]
vias = [t for t in b.GetTracks() if t.GetClass() == "PCB_VIA" and t.GetNetCode() == gnd]
segs = [t for t in b.GetTracks() if t.GetClass() == "PCB_TRACK" and t.GetNetCode() == gnd]
for z in b.Zones():
    if z.GetIsRuleArea() or z.GetNetCode() != gnd: continue
    for l in z.GetLayerSet().Seq():
        polys = z.GetFilledPolysList(l)
        areas = [(i, polys.Outline(i).Area() / 1e12) for i in range(polys.OutlineCount())]
        main = max(areas, key=lambda a: a[1])[0]
        for i, a in areas:
            if i == main: continue
            o = polys.Outline(i)
            inpads = [n for n, pt, ls in pads if ls.Contains(l) and o.PointInside(pt)]
            invias = [round(v.GetPosition().x / 1e6, 1) for v in vias if o.PointInside(v.GetPosition())]
            insegs = sum(1 for s in segs if s.GetLayer() == l and (o.PointInside(s.GetStart()) or o.PointInside(s.GetEnd())))
            bb = o.BBox()
            print(f"{z.GetZoneName()} island {i}: {a:.1f} mm2 at ({bb.GetLeft()/1e6:.0f},{bb.GetTop()/1e6:.0f})-({bb.GetRight()/1e6:.0f},{bb.GetBottom()/1e6:.0f}) pads={inpads} vias={invias} gnd-track-ends={insegs}")
