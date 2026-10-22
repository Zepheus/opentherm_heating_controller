"""Stage 1 of the routing pipeline: net classes, inset outline, rule areas, locked pre-routes, GND stitching, DSN export.

Everything Freerouting must not decide lives here as locked copper:
  - each relay contact (NC, COM, NO) to its terminal pin: straight 2.5 mm links, plus a link joining the contact's two pins;
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
rule_area("EDGE_GUARD_T", [(0, 0), (G.W, 0), (G.W, 2.2), (0, 2.2)])   # temporary: mains-to-edge 2 mm

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
            track(net, pcbnew.F_Cu, x, G.RY - G.PIN_DY, xr + G.TERM_DX[c], G.TERM_Y)    # straight up to its terminal pin
contact_links(track)

# ---- USB-C: interleaved D+/D- pads bridged on either side of the pad row, VBUS escaped past the locating holes
J1x, J1y = [(x, y) for (r, n), (x, y) in PADS.items() if r == "J1" and n == "A1"][0]
cx, py = J1x + 3.25, J1y                         # receptacle centre x; pad row y
DN = "/Power + MCU/USB_DN_C"; DP = "/Power + MCU/USB_DP_C"; V5 = "+5V"
track(DN, pcbnew.F_Cu, cx - .75, py, cx - .75, py - 1.105, 0.2); track(DN, pcbnew.F_Cu, cx - .75, py - 1.105, cx + .25, py - 1.105, 0.2); track(DN, pcbnew.F_Cu, cx + .25, py - 1.105, cx + .25, py, 0.2)
track(DP, pcbnew.F_Cu, cx - .25, py, cx - .25, py + 1.145, 0.2); track(DP, pcbnew.F_Cu, cx - .25, py + 1.145, cx + .75, py + 1.145, 0.2); track(DP, pcbnew.F_Cu, cx + .75, py + 1.145, cx + .75, py, 0.2)
for s in (-1, 1):
    x0 = cx + s * 2.45
    track(V5, pcbnew.F_Cu, x0, py, x0, py + .645, 0.3); track(V5, pcbnew.F_Cu, x0, py + .645, x0 - s * .4, py + 1.145, 0.3)
    track(V5, pcbnew.F_Cu, x0 - s * .4, py + 1.145, x0 - s * .4, py + 3.045, 0.3); via(V5, x0 - s * .4, py + 3.045)
track(V5, pcbnew.B_Cu, cx - 2.05, py + 3.045, cx + 2.05, py + 3.045, 0.6)
track(V5, pcbnew.B_Cu, cx + 2.05, py + 3.045, cx + 5.5, py + 3.045, 0.6); via(V5, cx + 5.5, py + 3.045)   # +5V picked up here by the router
USB_BOX = (cx - 6, py - 2, cx + 6.5, py + 4.5)

# ---- GND stitching grid over the low-voltage area
def stitching():
    boxes = list(BOXES) + [USB_BOX]
    ax0, ay0 = G.ANTENNA[0]; ax1, ay1 = G.ANTENNA[2]
    n = 0
    for xi in range(6, int(G.W) - 3, 10):
        for yi in range(int(G.SELV_TOP) + 4, int(G.H) - 3, 8):
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
