"""Stage 1 of the routing pipeline: net classes, inset outline, rule areas, locked pre-routes, GND stitching, DSN export.

Everything Freerouting must not decide lives here as locked copper:
  - each relay contact (NC, COM, NO) to its terminal pin below: straight 2.5 mm links, plus a link joining the contact's two pins;
  - the USB-C D+/D- pad bridges and the VBUS escape past the receptacle's locating holes;
  - a GND stitching-via grid over the low-voltage area so the bottom pour stays in one piece.
Temporary routing keep-outs cover each channel's contact area (removed after the SES import); the isolation band under
the contacts and the antenna keep-out are permanent rule areas.
usage: <kicad python> -I prep_board.py <project_dir>
"""
import sys, json, shutil, os, importlib.util, pcbnew
from pcbnew import FromMM, VECTOR2I
_here = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("geometry", os.path.join(_here, "..", "layout", "geometry.py"))
G = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(G)

P = sys.argv[1]
B = P + "/heating-controller.kicad_pcb"; PRO = P + "/heating-controller.kicad_pro"

# ---- net classes: one class per relay channel so channel-to-channel isolation can be a DRC rule. Low-voltage clearance
#      0.25 mm (JLC can do 0.127): no track fits between two 1.27 mm-pitch module pads, so every pin escapes straight out.
pro = json.load(open(PRO)); ns = pro.setdefault("net_settings", {})
base = dict(ns["classes"][0])
def cls(name, clear, tw, vd, vdr, prio):
    c = dict(base); c.update({"name": name, "clearance": clear, "track_width": tw, "via_diameter": vd, "via_drill": vdr, "priority": prio}); return c
ns["classes"] = [cls("Default", 0.25, 0.3, 0.8, 0.4, 2147483647)] + \
                [cls(f"CH{n}", 2.0, G.LINK_W, 1.6, 0.8, n - 1) for n in range(1, 5)] + [cls("USB", 0.2, 0.2, 0.8, 0.4, 9), cls("Power", 0.25, 0.6, 0.8, 0.4, 10)]
ns["netclass_patterns"] = [{"netclass": f"CH{n}", "pattern": G.contact_net(n, c)} for n in range(1, 5) for c in G.COL_DX] + \
                          [{"netclass": "USB", "pattern": "/Power + MCU/" + n} for n in ["USB_DN_C", "USB_DP_C", "USB_DN", "USB_DP", "CC1", "CC2"]] + \
                          [{"netclass": "Power", "pattern": p} for p in ["+5V", "+3V3", "GND"]]
rules = pro["board"]["design_settings"]["rules"]; rules["min_copper_edge_clearance"] = 0.3; rules["min_track_width"] = 0.15; rules["solder_mask_min_width"] = 0.0
pro_text = json.dumps(pro, indent=2); open(PRO, "w").write(pro_text); shutil.copy(PRO, P + "/fab/route/project.kicad_pro.bak")
print("netclasses written:", [c["name"] for c in ns["classes"]])

sm = pcbnew.GetSettingsManager(); sm.LoadProject(PRO)
board = pcbnew.LoadBoard(B)
# footprint data read right after loading (footprint proxies go stale later in this process)
BOXES, PADS, PAD_BOXES = [], {}, []
for f in board.Footprints():
    c = f.GetCourtyard(pcbnew.F_CrtYd); bb = c.BBox() if c.OutlineCount() else f.GetBoundingBox(False, False)
    BOXES.append(tuple(v / 1e6 for v in (bb.GetLeft(), bb.GetTop(), bb.GetRight(), bb.GetBottom())))
    for p in f.Pads():
        PADS[(f.GetReference(), p.GetNumber())] = (p.GetPosition().x / 1e6, p.GetPosition().y / 1e6)
        pb = p.GetBoundingBox(); PAD_BOXES.append(tuple(v / 1e6 for v in (pb.GetLeft(), pb.GetTop(), pb.GetRight(), pb.GetBottom())))

# outline inset 0.15 mm for the router; route_board.py restores the true outline
for d in list(board.GetDrawings()):
    if d.GetLayer() == pcbnew.Edge_Cuts: board.Remove(d)
sh = pcbnew.PCB_SHAPE(board); sh.SetShape(pcbnew.SHAPE_T_RECT); sh.SetLayer(pcbnew.Edge_Cuts)
sh.SetStart(VECTOR2I(FromMM(0.15), FromMM(0.15))); sh.SetEnd(VECTOR2I(FromMM(G.W - 0.15), FromMM(G.H - 0.15))); sh.SetWidth(FromMM(0.1)); board.Add(sh)

def rule_area(name, pts, layers=("F.Cu", "B.Cu"), tracks=True, vias=True, pour=True):
    z = pcbnew.ZONE(board); z.SetIsRuleArea(True); z.SetDoNotAllowTracks(tracks); z.SetDoNotAllowVias(vias); z.SetDoNotAllowZoneFills(pour)
    z.SetDoNotAllowPads(False); z.SetDoNotAllowFootprints(False)
    ls = pcbnew.LSET()
    for l in layers: ls.addLayer(pcbnew.F_Cu if l == "F.Cu" else pcbnew.B_Cu)
    z.SetLayerSet(ls); z.SetZoneName(name)
    for x, y in pts: z.AppendCorner(VECTOR2I(FromMM(x), FromMM(y)), -1, False)
    board.Add(z)
for n, xr in enumerate(G.RX, start=1):
    rule_area("ISOLATION_BAND", G.isolation_band(xr))
    rule_area(f"CH{n}_ZONE", G.channel_zone(xr))         # temporary: routing keep-out over the contact copper
rule_area("ANTENNA_KEEPOUT", G.ANTENNA)
for xr in G.RX:   # temporary: the isolation slots are only cut after routing, so keep the router off them
    for i, (x1, y1, x2, y2) in enumerate(G.slots(xr)):
        rule_area(f"SLOT{int(xr)}_{i}_ZONE", [(x1 - 0.6, y1 - 0.6), (x2 + 0.6, y1 - 0.6), (x2 + 0.6, y2 + 0.6), (x1 - 0.6, y2 + 0.6)])
rule_area("EDGE_GUARD_B", [(0, G.H - 2.2), (G.W, G.H - 2.2), (G.W, G.H), (0, G.H)])   # temporary: no router copper along the cable edge

def track(net, layer, x1, y1, x2, y2, w=G.LINK_W):
    t = pcbnew.PCB_TRACK(board); t.SetStart(VECTOR2I(FromMM(x1), FromMM(y1))); t.SetEnd(VECTOR2I(FromMM(x2), FromMM(y2)))
    t.SetWidth(FromMM(w)); t.SetLayer(layer); t.SetNet(board.FindNet(net)); t.SetLocked(True); board.Add(t)
def via(net, x, y, d=0.8, drill=0.4):
    v = pcbnew.PCB_VIA(board); v.SetPosition(VECTOR2I(FromMM(x), FromMM(y))); v.SetWidth(FromMM(d)); v.SetDrill(FromMM(drill))
    v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu); v.SetNet(board.FindNet(net)); v.SetLocked(True); board.Add(v)

def contact_links(track):
    for n, xr in enumerate(G.RX, start=1):
        for c, dx in G.COL_DX.items():
            net = G.contact_net(n, c); x = xr + dx
            track(net, pcbnew.F_Cu, x, G.RY + G.PIN_DY, x, G.RY - G.PIN_DY)              # join the contact's two pins
            track(net, pcbnew.F_Cu, x, G.RY + G.PIN_DY, xr + G.TERM_DX[c], G.TERM_Y)    # straight down to its terminal pin
contact_links(track)

# ---- +5V rail above the drivers, with a B.Cu drop to each coil's +5V pin (pin 1, on the row nearest the terminals)
track("+5V", pcbnew.F_Cu, G.RAIL_X[0], G.RAIL_Y, G.RAIL_X[1], G.RAIL_Y, G.RAIL_W)
for xr in G.RX:
    x0 = xr + G.COIL_DX; xd = x0 + G.COIL_DROP_DX
    via("+5V", xd, G.RAIL_Y, 1.0, 0.5)
    track("+5V", pcbnew.B_Cu, xd, G.RAIL_Y, xd, G.RY + G.PIN_DY, G.RAIL_W); track("+5V", pcbnew.B_Cu, xd, G.RY + G.PIN_DY, x0, G.RY + G.PIN_DY, G.RAIL_W)
    n_ = G.RX.index(xr) + 1
    rl = PADS[(f"R1{n_}3", "1")]; track("+5V", pcbnew.F_Cu, rl[0], G.RAIL_Y, rl[0], rl[1], 0.6)          # LED resistor
    qs = PADS[(f"Q10{n_}", "2")]; via("GND", qs[0] - 1.6, qs[1]); track("GND", pcbnew.F_Cu, qs[0] - 1.6, qs[1], qs[0], qs[1], 0.5)   # coil current return
    dd = PADS[(f"D10{n_}", "1")]; via("+5V", xd, dd[1] + 1.45); track("+5V", pcbnew.F_Cu, xd, dd[1] + 1.45, dd[0], dd[1], 0.5)   # flyback cathode

# ---- +5V feed: USB VBUS via -> B.Cu trunk at x FX down to the rail; via at the TVS / bulk capacitor; B.Cu branch to the
#      regulator input. The router only adds the receptacle-to-ESD link and the drivers' short stubs.
FX = G.RAIL_X[0]
def pad(ref, n): return PADS[(ref, n)]
d1, c2, c3, u2 = pad("D1", "1"), pad("C2", "1"), pad("C3", "1"), pad("U2", "3")
track("+5V", pcbnew.B_Cu, FX, 30.0, FX, G.RAIL_Y, 0.8); via("+5V", FX, G.RAIL_Y, 1.0, 0.5)
via("+5V", FX, d1[1] - 0.4); track("+5V", pcbnew.F_Cu, FX, d1[1] - 0.4, c2[0], c2[1], 0.8); track("+5V", pcbnew.F_Cu, FX, d1[1] - 0.4, d1[0], d1[1], 0.6)
RY_ = c3[1] + 2.55
track("+5V", pcbnew.B_Cu, FX, RY_, c3[0], RY_, 0.6); via("+5V", c3[0], RY_)
track("+5V", pcbnew.F_Cu, c3[0], RY_, c3[0], c3[1], 0.6); track("+5V", pcbnew.F_Cu, c3[0], RY_, u2[0], u2[1], 0.6)

# ---- USB-C: interleaved D+/D- pads bridged on either side of the pad row, VBUS escaped past the locating holes.
# Drawn in the receptacle's own frame (u along the pad row A1 -> A12, v towards the plug opening), then mapped to the
# board, so any rotation of J1 works.
A1 = PADS[("J1", "A1")]; A12 = PADS[("J1", "A12")]
L = ((A12[0] - A1[0]) ** 2 + (A12[1] - A1[1]) ** 2) ** 0.5
U = ((A12[0] - A1[0]) / L, (A12[1] - A1[1]) / L); V = (-U[1], U[0])
C0 = ((A1[0] + A12[0]) / 2, (A1[1] + A12[1]) / 2)   # receptacle centre on the pad row
def at(du, dv): return (C0[0] + du * U[0] + dv * V[0], C0[1] + du * U[1] + dv * V[1])
def tr(net, layer, a, b, w):
    (x1, y1), (x2, y2) = at(*a), at(*b); track(net, layer, x1, y1, x2, y2, w)
DN = "/Power + MCU/USB_DN_C"; DP = "/Power + MCU/USB_DP_C"; V5 = "+5V"
for a, b in [((-.75, 0), (-.75, -1.105)), ((-.75, -1.105), (.25, -1.105)), ((.25, -1.105), (.25, 0))]: tr(DN, pcbnew.F_Cu, a, b, 0.2)
for a, b in [((-.25, 0), (-.25, 1.145)), ((-.25, 1.145), (.75, 1.145)), ((.75, 1.145), (.75, 0))]: tr(DP, pcbnew.F_Cu, a, b, 0.2)
for s_ in (-1, 1):
    u0 = s_ * 2.45
    tr(V5, pcbnew.F_Cu, (u0, 0), (u0, .645), 0.3); tr(V5, pcbnew.F_Cu, (u0, .645), (u0 - s_ * .4, 1.145), 0.3)
    tr(V5, pcbnew.F_Cu, (u0 - s_ * .4, 1.145), (u0 - s_ * .4, 3.045), 0.3); via(V5, *at(u0 - s_ * .4, 3.045))
tr(V5, pcbnew.B_Cu, (-2.05, 3.045), (2.05, 3.045), 0.6)
tr(V5, pcbnew.B_Cu, (2.05, 3.045), (5.5, 3.045), 0.6)
_vx, _vy = at(5.5, 3.045); track(V5, pcbnew.B_Cu, _vx, _vy, FX, _vy, 0.8)   # on to the +5V trunk
# ESD array VBUS pin: its only free side faces away from the receptacle; via above it, B.Cu back to the VBUS track
e5 = PADS[("U3", "5")]; ev = (e5[0], e5[1] - 1.55); via(V5, *ev); track(V5, pcbnew.F_Cu, ev[0], ev[1], e5[0], e5[1], 0.4)
for su in (-3.25, 3.25):   # GND pads at both ends of the row: via straight in from the pad, before CC/SBU claim the space
    tr("GND", pcbnew.F_Cu, (su, 0), (su, -1.3), 0.4); via("GND", *at(su, -1.3))
e2 = PADS[("U3", "2")]; via("GND", e2[0], e2[1] + 1.4); track("GND", pcbnew.F_Cu, e2[0], e2[1] + 1.4, e2[0], e2[1], 0.4)   # ESD ground, boxed in by D+/D-
_mx, _my = at(0, 3.045); track(V5, pcbnew.B_Cu, ev[0], ev[1], ev[0] - 2.6, _my, 0.5); track(V5, pcbnew.B_Cu, ev[0] - 2.6, _my, _mx, _my, 0.5)
_bc = [at(du, dv) for du in (-6, 6.5) for dv in (-2, 4.5)]
USB_BOX = (min(x for x, _ in _bc), min(y for _, y in _bc), max(x for x, _ in _bc), max(y for _, y in _bc))
print("USB-C frame: u", tuple(round(v, 3) for v in U), "v", tuple(round(v, 3) for v in V), "centre", tuple(round(v, 2) for v in C0))

# ---- GND stitching grid over the low-voltage area
def stitching():
    boxes = list(BOXES) + [USB_BOX]
    ax0, ay0 = G.ANTENNA[0]; ax1, ay1 = G.ANTENNA[2]
    n = 0
    for xi in range(6, int(G.W) - 3, 10):
        for yi in range(4, int(G.SELV_BOTTOM) - 1, 8):
            x, y = float(xi), float(yi)
            if ax0 - 1 <= x <= ax1 + 1 and ay0 - 1 <= y <= ay1 + 1: continue
            if any(x0 - 1.0 <= x <= x1 + 1.0 and y0 - 1.0 <= y <= y1 + 1.0 for x0, y0, x1, y1 in boxes): continue
            if any(x0 - 1.0 <= x <= x1 + 1.0 and y0 - 1.0 <= y <= y1 + 1.0 for x0, y0, x1, y1 in PAD_BOXES): continue   # some EasyEDA pads stick out of the courtyard
            via("GND", x, y); n += 1
    print("stitching vias:", n)
stitching()

board.GetDesignSettings().m_SolderMaskMinWidth = 0
pcbnew.SaveBoard(B, board)
print("zones:", len(board.Zones()))
ok = pcbnew.ExportSpecctraDSN(board, P + "/fab/route/heating-controller.dsn"); print("dsn export:", ok)
open(PRO, "w").write(pro_text)
for f in os.listdir(P):
    if f.endswith(".lck"): os.remove(os.path.join(P, f))
