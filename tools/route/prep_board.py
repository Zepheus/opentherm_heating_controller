"""Stage 1 (KiCad closed): netclasses -> .kicad_pro, square (inset) outline, keepouts, locked mains buses, DSN export."""
import sys, json, shutil, os, pcbnew
from pcbnew import FromMM, VECTOR2I
P=sys.argv[1]
B=P+"/heating-controller.kicad_pcb"; PRO=P+"/heating-controller.kicad_pro"

pro=json.load(open(PRO)); ns=pro.setdefault("net_settings",{})
base=dict(ns["classes"][0])
def cls(name,clear,tw,vd,vdr,prio):
    c=dict(base); c.update({"name":name,"clearance":clear,"track_width":tw,"via_diameter":vd,"via_drill":vdr,"priority":prio}); return c
ns["classes"]=[cls("Default",0.2,0.3,0.8,0.4,2147483647), cls("MAINS",2.0,2.5,1.6,0.8,0), cls("MAINS_SENSE",0.5,0.5,1.0,0.5,1), cls("Power",0.2,0.6,0.8,0.4,2)]
mains=["/Mains IO/MAINS_L","/Mains IO/MAINS_N","/Mains IO/DEMAND_RET"]+[f"/Mains IO/COM{n}" for n in range(1,5)]+[f"/Mains IO/NO{n}" for n in range(1,5)]
sense=["/Mains IO/DEMAND_230","/Mains IO/DEMAND_24","/Mains IO/ES1_IN","/Mains IO/ES2_IN","/Mains IO/ES3_IN"]
sense+=[f"/Mains IO/S{k}_{i}" for k in range(1,6) for i in range(1,6)]+[f"/Mains IO/LEDA{k}" for k in range(1,6)]+[f"/Mains IO/LEDK{k}" for k in range(1,6)]
ns["netclass_patterns"]=[{"netclass":"MAINS","pattern":m} for m in mains]+[{"netclass":"MAINS_SENSE","pattern":m} for m in sense]+[{"netclass":"Power","pattern":p} for p in ["+5V","+3V3","GND"]]
rules=pro["board"]["design_settings"]["rules"]; rules["min_copper_edge_clearance"]=0.3; rules["min_track_width"]=0.15; rules["solder_mask_min_width"]=0.0
pro_text=json.dumps(pro, indent=2); open(PRO,"w").write(pro_text); shutil.copy(PRO, P+"/fab/route/project.kicad_pro.bak")
print("netclasses written:", [c["name"] for c in ns["classes"]], "patterns:", len(ns["netclass_patterns"]))

sm=pcbnew.GetSettingsManager(); sm.LoadProject(PRO)
board=pcbnew.LoadBoard(B)
# courtyard boxes, read before the board is edited (footprint proxies go stale later in this process)
COURTYARD_BOXES=[]
for f in board.Footprints():
    c=f.GetCourtyard(pcbnew.F_CrtYd); bb=c.BBox() if c.OutlineCount() else f.GetBoundingBox(False,False)
    COURTYARD_BOXES.append(tuple(v/1e6 for v in (bb.GetLeft(),bb.GetTop(),bb.GetRight(),bb.GetBottom())))
for d in list(board.GetDrawings()):
    if d.GetLayer()==pcbnew.Edge_Cuts: board.Remove(d)
sh=pcbnew.PCB_SHAPE(board); sh.SetShape(pcbnew.SHAPE_T_RECT); sh.SetLayer(pcbnew.Edge_Cuts)
sh.SetStart(VECTOR2I(FromMM(0.15),FromMM(0.15))); sh.SetEnd(VECTOR2I(FromMM(149.85),FromMM(94.85))); sh.SetWidth(FromMM(0.1)); board.Add(sh)

def rule_area(name, pts, layers=("F.Cu","B.Cu"), tracks=True, vias=True, pour=True):
    z=pcbnew.ZONE(board); z.SetIsRuleArea(True); z.SetDoNotAllowTracks(tracks); z.SetDoNotAllowVias(vias); z.SetDoNotAllowZoneFills(pour)
    z.SetDoNotAllowPads(False); z.SetDoNotAllowFootprints(False)
    ls=pcbnew.LSET()
    for l in layers: ls.addLayer(pcbnew.F_Cu if l=="F.Cu" else pcbnew.B_Cu)
    z.SetLayerSet(ls); z.SetZoneName(name)
    for x,y in pts: z.AppendCorner(VECTOR2I(FromMM(x),FromMM(y)), -1, False)
    board.Add(z)
rule_area("ISOLATION_BAND", [(0,30),(93.5,30),(93.5,48.5),(150,48.5),(150,55.5),(88,55.5),(88,39),(0,39)])
rule_area("ANTENNA_KEEPOUT", [(3,87.2),(29,87.2),(29,95),(3,95)])
rule_area("MAINS_BUS_CORRIDOR_F", [(0,10.5),(138,10.5),(138,21.5),(0,21.5)], layers=("F.Cu",))
rule_area("MAINS_BUS_CORRIDOR_B", [(94,10.5),(138,10.5),(138,26.5),(94,26.5)], layers=("B.Cu",))
# edge guards: keep routed copper 2 mm off the edges of the 230 V region (removed after routing)
rule_area("EDGE_GUARD_T", [(0,0),(150,0),(150,2.2),(0,2.2)])
rule_area("EDGE_GUARD_R", [(147.8,0),(150,0),(150,48.5),(147.8,48.5)])
rule_area("EDGE_GUARD_L", [(0,0),(2.2,0),(2.2,39),(0,39)])

# locked mains buses (exported to the DSN as fixed wiring)
L="/Mains IO/MAINS_L"; N="/Mains IO/MAINS_N"
def track(net, layer, x1,y1,x2,y2, w=2.5):
    t=pcbnew.PCB_TRACK(board); t.SetStart(VECTOR2I(FromMM(x1),FromMM(y1))); t.SetEnd(VECTOR2I(FromMM(x2),FromMM(y2)))
    t.SetWidth(FromMM(w)); t.SetLayer(layer); t.SetNet(board.FindNet(net)); t.SetLocked(True); board.Add(t)
def via(net, x,y, d=1.6, drill=0.8):
    v=pcbnew.PCB_VIA(board); v.SetPosition(VECTOR2I(FromMM(x),FromMM(y))); v.SetWidth(FromMM(d)); v.SetDrill(FromMM(drill))
    v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu); v.SetNet(board.FindNet(net)); v.SetLocked(True); board.Add(v)
def buses():
    # L bus nearest the terminals (y 12.5) so its drops to J111..J114 pin 1 never cross N; N bus at y 17
    track(L,pcbnew.F_Cu,14.5,8,14.5,12.5); track(L,pcbnew.F_Cu,14.5,12.5,131,12.5)
    for x in [27,44,61,78]: track(L,pcbnew.F_Cu,x,12.5,x,8)
    via(L,131,12.5); track(L,pcbnew.B_Cu,131,12.5,131,23.2); via(L,131,23.2); track(L,pcbnew.F_Cu,131,23.2,131,24.3,2.0)
    track(N,pcbnew.B_Cu,19.5,8,19.5,17); via(N,19.5,17); track(N,pcbnew.F_Cu,19.5,17,135,17)
    for x in [99,108,117,135]:
        via(N,x,17); track(N,pcbnew.B_Cu,x,17,x,23.2); via(N,x,23.2); track(N,pcbnew.F_Cu,x,23.2,x,24.3,2.0)
buses()
# USB-C: the D+/D- pad pairs are interleaved, so bridge D- on the inner side, D+ on the outer side, and take
# VBUS off through vias on B.Cu, all as fixed wiring so the router never has to discover this itself
DN="/Power + MCU/USB_DN_C"; DP="/Power + MCU/USB_DP_C"; V5="+5V"
track(DN,pcbnew.F_Cu,39.25,86.455,39.25,85.35,0.2); track(DN,pcbnew.F_Cu,39.25,85.35,40.25,85.35,0.2); track(DN,pcbnew.F_Cu,40.25,85.35,40.25,86.455,0.2)
track(DP,pcbnew.F_Cu,39.75,86.455,39.75,87.6,0.2); track(DP,pcbnew.F_Cu,39.75,87.6,40.75,87.6,0.2); track(DP,pcbnew.F_Cu,40.75,87.6,40.75,86.455,0.2)
track(V5,pcbnew.F_Cu,37.55,86.455,37.55,87.1,0.3); track(V5,pcbnew.F_Cu,37.55,87.1,37.95,87.6,0.3); track(V5,pcbnew.F_Cu,37.95,87.6,37.95,89.5,0.3); via(V5,37.95,89.5,0.8,0.4)
track(V5,pcbnew.F_Cu,42.45,86.455,42.45,87.1,0.3); track(V5,pcbnew.F_Cu,42.45,87.1,42.05,87.6,0.3); track(V5,pcbnew.F_Cu,42.05,87.6,42.05,89.5,0.3); via(V5,42.05,89.5,0.8,0.4)
track(V5,pcbnew.B_Cu,37.95,89.5,42.05,89.5,0.6)
track(V5,pcbnew.B_Cu,42.05,89.5,53,89.5,0.6); via(V5,53,89.5,0.8,0.4); track(V5,pcbnew.F_Cu,53,89.5,53,87.4,0.6)
# relay contacts + DEMAND_RET, fixed so the router works around them
def contacts_and_demand():
    for n,xt in enumerate([32,49,66,83], start=1):
        for net,xp,xr in [(f"/Mains IO/COM{n}",xt,xt-2.55),(f"/Mains IO/NO{n}",xt+5,xt+3.8)]:
            track(net,pcbnew.B_Cu,xp,8,xp,19); track(net,pcbnew.B_Cu,xp,19,xr,25.38)
    DR="/Mains IO/DEMAND_RET"
    track(DR,pcbnew.B_Cu,143.5,25,140.5,28); track(DR,pcbnew.B_Cu,140.5,28,126,28); track(DR,pcbnew.B_Cu,126,28,126,23.2)
    via(DR,126,23.2); track(DR,pcbnew.F_Cu,126,23.2,126,24.3,2.0)
contacts_and_demand()
# GND stitching vias on a 10 mm grid inside the SELV region, fixed before routing so the router works around them.
# Without them, long B.Cu tracks along the isolation band slice the bottom pour into islands that KiCad then removes.
def stitching():
    boxes=list(COURTYARD_BOXES)
    boxes.append((36,84,54,92))  # USB fixed wiring
    n=0
    for xi in range(6,147,10):
        for yi in range(42,93,10):
            x,y=float(xi),float(yi)
            if x>88.5 and y<58: continue          # isolation band is y 48.5-55.5 here
            if x>86 and x<96 and y<58: continue   # band step
            if x<30 and y>85.5: continue          # antenna keep-out
            if any(x0-1.0<=x<=x1+1.0 and y0-1.0<=y<=y1+1.0 for x0,y0,x1,y1 in boxes): continue
            via("GND",x,y,0.8,0.4); n+=1
    print("stitching vias:", n)
stitching()
board.GetDesignSettings().m_SolderMaskMinWidth=0
pcbnew.SaveBoard(B, board)
print("zones:", len(board.Zones()))
ok=pcbnew.ExportSpecctraDSN(board, P+"/fab/route/heating-controller.dsn"); print("dsn export:", ok)
open(PRO,"w").write(pro_text)
for f in os.listdir(P):
    if f.endswith(".lck"): os.remove(os.path.join(P,f))
