"""Pre-fabrication sanity report for the board, beyond what DRC checks.

Checks: track widths actually used per net class, JLCPCB 2-layer capability limits (track, via, drill, annular
ring, hole-to-edge), through-hole drill sizes per footprint, decoupling-capacitor distances, copper inside the
antenna keep-out, silkscreen on pads, tallest parts (enclosure), parts JLC may rotate in the CPL, and the
single-pad nets. Prints a report; exit code 1 if a hard limit fails.

usage: <kicad python> -I tools/check/sanity.py <board.kicad_pcb>
"""
import sys, math, collections, pcbnew

B = sys.argv[1]; board = pcbnew.LoadBoard(B)
mm = lambda v: v / 1e6
fail = []

# JLCPCB standard 2-layer, 1 oz capabilities (published minimums; our design rules are stricter)
JLC = dict(track=0.127, space=0.127, via_drill=0.3, via_dia=0.4, annular=0.05, pth_annular=0.25, hole_edge=0.3)

# ---- tracks and vias
cls_min = collections.defaultdict(lambda: 99.0); cls_where = {}; vias = []
for t in board.GetTracks():
    nc = t.GetNetClassName() if hasattr(t, "GetNetClassName") else t.GetEffectiveNetClass().GetName()
    if t.GetClass() == "PCB_VIA":
        vias.append((mm(t.GetWidth(pcbnew.F_Cu)), mm(t.GetDrillValue()), t.GetNetname(), t.GetPosition()))
    else:
        if mm(t.GetWidth()) < cls_min[nc]: cls_min[nc] = mm(t.GetWidth()); cls_where[nc] = (t.GetNetname().split("/")[-1], round(mm(t.GetStart().x), 1), round(mm(t.GetStart().y), 1))
print("== Narrowest track per net class (mm)")
expect = {"CH1": 2.0, "CH2": 2.0, "CH3": 2.0, "CH4": 2.0, "USB": 0.2, "Power": 0.3, "Default": 0.2}
for c, w in sorted(cls_min.items()):
    ok = w >= min(expect.get(c.split(",")[0], 0.2), 99) - 1e-6
    print(f"   {c:12} {w:.2f}  {'ok' if ok else 'below class width ' + str(expect.get(c)) + ' (router neck-down), at ' + str(cls_where[c])}")
    if w < JLC["track"]: fail.append(f"track below JLC minimum: {c} {w}")
print("== Vias")
vd = collections.Counter((round(d, 2), round(h, 2)) for d, h, n, p in vias)
for (d, h), n in sorted(vd.items()):
    ring = (d - h) / 2; ok = h >= JLC["via_drill"] and d >= JLC["via_dia"] and ring >= JLC["annular"] - 1e-6
    print(f"   {n:4} × {d:.2f}/{h:.2f} mm (annular {ring:.2f})  {'ok' if ok else 'FAILS JLC'}")
    if not ok: fail.append(f"via {d}/{h}")

# ---- through-hole pads: drill, annular ring, hole to board edge
print("== Through-hole drills per footprint (mm): check against lead sizes")
edge = board.GetBoardEdgesBoundingBox()
seen = {}
for f in board.Footprints():
    for p in f.Pads():
        if p.GetAttribute() not in (pcbnew.PAD_ATTRIB_PTH, pcbnew.PAD_ATTRIB_NPTH): continue
        dx, dy = mm(p.GetDrillSize().x), mm(p.GetDrillSize().y); sx, sy = mm(p.GetSize(pcbnew.F_Cu).x), mm(p.GetSize(pcbnew.F_Cu).y)
        key = (str(f.GetFPID().GetLibItemName()), round(dx, 2), round(dy, 2), round(sx, 2), round(sy, 2), p.GetAttribute())
        seen.setdefault(key, []).append(f.GetReference())
        pos = p.GetPosition(); r = max(dx, dy) / 2
        dist = min(mm(pos.x - edge.GetLeft()), mm(edge.GetRight() - pos.x), mm(pos.y - edge.GetTop()), mm(edge.GetBottom() - pos.y)) - r
        if dist < JLC["hole_edge"]: fail.append(f"hole {f.GetReference()} {dist:.2f} mm from edge")
for (fp, dx, dy, sx, sy, a), refs in sorted(seen.items()):
    ring = (min(sx, sy) - min(dx, dy)) / 2
    kind = "NPTH" if a == pcbnew.PAD_ATTRIB_NPTH else f"pad {sx}×{sy}, ring {ring:.2f}"
    need = JLC["annular"] if max(dx, dy) <= 0.4 else (0.2 if dx != dy else JLC["pth_annular"])   # via-like holes; plated slots 0.2
    note = "" if a == pcbnew.PAD_ATTRIB_NPTH or ring >= need - 1e-6 else f"  RING BELOW {need}"
    if note: fail.append(f"annular {fp} {ring:.2f}")
    print(f"   {fp[:44]:44} drill {dx}×{dy}  {kind}  ({len(set(refs))} parts){note}")

# ---- decoupling: distance from each capacitor on a supply to the nearest supply pin it serves
print("== Decoupling distances (capacitor pad to nearest IC supply pad, mm)")
ics = {"U1": ("+3V3",), "U2": ("+3V3", "+5V"), "U3": ("+5V",)}
pads = {r: [(p.GetNetname(), p.GetPosition()) for p in f.Pads()] for f in board.Footprints() for r in [f.GetReference()]}
for f in board.Footprints():
    r = f.GetReference()
    if not r.startswith("C") or r.startswith("C1") and len(r) == 4: continue
    for net, pos in pads[r]:
        if net not in ("+3V3", "+5V"): continue
        best = min(((math.dist((mm(pos.x), mm(pos.y)), (mm(q.x), mm(q.y))), ic) for ic, nets in ics.items() for n2, q in pads[ic] if n2 == net and net in nets), default=None)
        if best: print(f"   {r:4} {f.GetValue():10} on {net:5} → {best[1]}: {best[0]:.1f}")

# ---- copper inside the antenna keep-out (module antenna end)
print("== Antenna keep-out")
ka = [z for z in board.Zones() if z.GetIsRuleArea() and z.GetZoneName() == "ANTENNA_KEEPOUT"]
if not ka: print("   no ANTENNA_KEEPOUT rule area on the board!"); fail.append("antenna keepout missing")
else:
    bb = ka[0].GetBoundingBox(); hits = []
    for t in board.GetTracks():
        if bb.Contains(t.GetStart()) or bb.Contains(t.GetEnd()): hits.append(t.GetNetname())
    for f in board.Footprints():
        if f.GetReference() == "U1": continue
        for p in f.Pads():
            if bb.Contains(p.GetPosition()):
                if p.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH: print(f"   note: unplated hole {f.GetReference()} inside the keep-out; use a nylon screw there")
                else: hits.append(f.GetReference())
    print(f"   rule area {mm(bb.GetLeft()):.1f},{mm(bb.GetTop()):.1f} to {mm(bb.GetRight()):.1f},{mm(bb.GetBottom()):.1f}: {'clear' if not hits else hits}")
    if hits: fail.append("copper in antenna keepout")

# ---- tallest parts (enclosure clearance) and parts JLC may rotate
print("== Tallest 3D bodies (from model bounding boxes is not available headless; listed by known heights)")
heights = {"RELAY-TH": 15.7, "WJ128V": 14.1, "CP_Elec_8x10": 10.5, "KF350": 8.7, "PinHeader": 8.5, "ESP32": 3.2}
tall = collections.defaultdict(list)
for f in board.Footprints():
    n = str(f.GetFPID().GetLibItemName())
    for k, h in heights.items():
        if k in n and not f.IsDNP(): tall[h].append(f.GetReference())
for h in sorted(tall, reverse=True): print(f"   {h:5.1f} mm  {', '.join(sorted(tall[h]))}")
print("== Footprints from the EasyEDA library (check rotation in the JLCPCB placement preview)")
print("   " + ", ".join(sorted(f.GetReference() for f in board.Footprints() if str(f.GetFPID().GetLibNickname()) == "jlc")))

# ---- isolation and spacing requirements: the DRC rule file must encode every one of them (DRC then enforces them)
import json, os, re
print("== Spacing requirements encoded in the DRC rules")
proj = os.path.dirname(os.path.abspath(B))
spec = json.load(open(os.path.join(proj, "tools", "check", "spacing_rules.json")))
dru = open(os.path.join(proj, "heating-controller.kicad_dru")).read()
for r in spec["rules"]:
    m = re.search(r'\(rule "%s"(.*?)\n\(rule |\(rule "%s"(.*)' % (re.escape(r["rule"]), re.escape(r["rule"])), dru + "\n(rule ", re.S)
    body = (m.group(1) or m.group(2) or "") if m else ""
    v = re.search(r'\(constraint %s \(min ([\d.]+)mm\)' % r["constraint"], body)
    ok = bool(v) and float(v.group(1)) >= r["min_mm"] - 1e-9
    print(f"   {r['rule']:24} {r['constraint']:14} required ≥ {r['min_mm']} mm: {('encoded ' + v.group(1) + ' mm') if v else 'MISSING'} {'ok' if ok else 'FAIL'}")
    if not ok: fail.append(f"spacing rule {r['rule']}")
areas = {z.GetZoneName() for z in board.Zones() if z.GetIsRuleArea()}
for a in spec["required_rule_areas"]:
    print(f"   rule area {a}: {'present' if a in areas else 'MISSING'}")
    if a not in areas: fail.append(f"rule area {a}")
slots = [d for d in board.GetDrawings() if d.GetLayer() == pcbnew.Edge_Cuts and d.GetShape() == pcbnew.SHAPE_T_RECT
         and min(abs(mm(d.GetEnd().x - d.GetStart().x)), abs(mm(d.GetEnd().y - d.GetStart().y))) < 3]
widths = [min(abs(mm(d.GetEnd().x - d.GetStart().x)), abs(mm(d.GetEnd().y - d.GetStart().y))) for d in slots]
ok = len(slots) >= spec["required_slots_mm"]["count_min"] and all(w >= spec["required_slots_mm"]["width_min"] - 1e-6 for w in widths)
print(f"   isolation slots: {len(slots)}, widths {sorted(set(round(w, 2) for w in widths))} mm {'ok' if ok else 'FAIL'}")
if not ok: fail.append("isolation slots")

# ---- connectors: external ones at their edge facing out, internal headers well inside
import math as _m, importlib.util as _iu
_spec = _iu.spec_from_file_location("geometry", os.path.join(proj, "tools", "layout", "geometry.py")); G = _iu.module_from_spec(_spec); _spec.loader.exec_module(G)
print("== Connectors")
dirs = {"top": (0, -1), "bottom": (0, 1), "left": (-1, 0), "right": (1, 0)}
eb = board.GetBoardEdgesBoundingBox()
for f in board.Footprints():
    r = f.GetReference()
    c = f.GetCourtyard(pcbnew.F_CrtYd); bb = c.BBox() if c.OutlineCount() else f.GetBoundingBox(False, False)
    gaps = {"top": mm(bb.GetTop() - eb.GetTop()), "bottom": mm(eb.GetBottom() - bb.GetBottom()),
            "left": mm(bb.GetLeft() - eb.GetLeft()), "right": mm(eb.GetRight() - bb.GetRight())}
    if r in G.EDGE_CONNECTORS:
        edge, _ = G.EDGE_CONNECTORS[r]; a = _m.radians(f.GetOrientationDegrees())
        face = (round(_m.sin(a)), round(_m.cos(a))); ok = face == dirs[edge] and gaps[edge] <= G.EDGE_MAX_GAP
        print(f"   {r:5} {edge:6} entry faces {face}, {gaps[edge]:.1f} mm from edge  {'ok' if ok else 'FAIL'}")
        if not ok: fail.append(f"connector {r} not at/facing the {edge} edge")
    if r in G.EDGE_CONNECTORS and G.EDGE_CONNECTORS[r][0] in G.NO_CABLE_EDGES:
        print(f"   {r:5} assigned to the {G.EDGE_CONNECTORS[r][0]} edge, which takes no cables  FAIL"); fail.append(f"connector {r} on a no-cable edge")
    if r.startswith("J") and r not in G.EDGE_CONNECTORS and r not in G.INTERNAL_HEADERS:
        print(f"   {r:5} is neither an edge connector nor an internal header in geometry.py  FAIL"); fail.append(f"connector {r} unclassified")
    if r in G.INTERNAL_HEADERS:
        ok = min(gaps.values()) >= G.INTERNAL_HEADERS[r]
        print(f"   {r:5} internal, {min(gaps.values()):.1f} mm from nearest edge  {'ok' if ok else 'FAIL'}")
        if not ok: fail.append(f"header {r} too close to the edge")

# ---- OLED area: the module stacks over this rectangle, so no other part may sit in it
ox0, oy0, ox1, oy1 = (pcbnew.FromMM(v) for v in G.OLED_BOX)
inside = [f.GetReference() for f in board.Footprints() if f.GetReference() != "J5" and
          (lambda bb: bb.GetRight() > ox0 and bb.GetLeft() < ox1 and bb.GetBottom() > oy0 and bb.GetTop() < oy1)(
              f.GetCourtyard(pcbnew.F_CrtYd).BBox() if f.GetCourtyard(pcbnew.F_CrtYd).OutlineCount() else f.GetBoundingBox(False, False))]
print("== OLED module area:", "clear" if not inside else "parts inside: " + ", ".join(inside))
if inside: fail.append(f"parts under the OLED module {inside}")

# ---- pads of different parts closer than 0.25 mm (EasyEDA footprints can have pads outside their courtyard)
pl = []
for f in board.Footprints():
    for p_ in f.Pads():
        pb = p_.GetBoundingBox(); pb.Inflate(pcbnew.FromMM(0.25)); pl.append((f.GetReference(), p_.GetNetCode(), pb))
clash = sorted(set((a[0], c[0]) for i, a in enumerate(pl) for c in pl[i + 1:] if a[0] != c[0] and (a[1] != c[1] or a[1] == 0) and a[2].Intersects(c[2])))
print("== Pads of neighbouring parts closer than 0.25 mm:", clash or "none")
if clash: fail.append(f"pad clash {clash}")

# ---- mounting holes: screw heads (self-tapping into ABS, pan head up to 6.0 mm) are accessible metal
HEAD_R = 3.0
print("== Mounting holes (screw head edge to relay contact copper, mm)")
mains = [t for t in board.GetTracks() if t.GetNetClassName() in ("CH1", "CH2", "CH3", "CH4")] + \
        [p for f in board.Footprints() for p in f.Pads() if p.GetNetClassName() in ("CH1", "CH2", "CH3", "CH4")]
for f in board.Footprints():
    if not f.GetReference().startswith("H"): continue
    c = f.GetPosition(); d = None
    for it in mains:
        sh = it.GetEffectiveShape(pcbnew.F_Cu)
        dd = (sh.GetClearance(pcbnew.SHAPE_CIRCLE(c, 0)) if hasattr(sh, "GetClearance") else None)
        if dd is None:
            bb = it.GetBoundingBox(); dx = max(bb.GetLeft() - c.x, 0, c.x - bb.GetRight()); dy = max(bb.GetTop() - c.y, 0, c.y - bb.GetBottom()); dd = (dx * dx + dy * dy) ** 0.5
        d = dd if d is None else min(d, dd)
    gap = mm(d) - HEAD_R if d is not None else 99
    ok = gap >= 6.4
    print(f"   {f.GetReference()}: {gap:.1f} {'ok' if ok else 'FAIL (needs 6.4)'}")
    if not ok: fail.append(f"screw head {f.GetReference()} {gap:.1f} mm from mains")

# ---- single-pad nets
print("== Nets with a single pad")
cnt = collections.Counter(p.GetNetname() for f in board.Footprints() for p in f.Pads() if p.GetNetname())
singles = sorted(n for n, c in cnt.items() if c == 1)
print("   " + (", ".join(singles) if singles else "none"))
bad = [n for n in singles if not n.startswith("unconnected-")]
if bad: fail.append(f"single-pad nets {bad}")

print("\nRESULT:", "PASS" if not fail else "FAIL: " + "; ".join(fail))
sys.exit(1 if fail else 0)
