"""Stage 2 (KiCad closed): import SES, drop corridor keepouts, re-add mains buses deterministically, slots, GND pours, fill, save."""
import sys, re, collections, pcbnew
from pcbnew import FromMM, VECTOR2I
P=sys.argv[1]; B=P+"/heating-controller.kicad_pcb"; SES=P+"/fab/route/heating-controller.ses"
PRO=P+"/heating-controller.kicad_pro"
pcbnew.GetSettingsManager().LoadProject(PRO)
board=pcbnew.LoadBoard(B)
for d in list(board.GetDrawings()):
    if d.GetLayer()==pcbnew.Edge_Cuts: board.Remove(d)
sh=pcbnew.PCB_SHAPE(board); sh.SetShape(pcbnew.SHAPE_T_RECT); sh.SetLayer(pcbnew.Edge_Cuts)
sh.SetStart(VECTOR2I(0,0)); sh.SetEnd(VECTOR2I(FromMM(150),FromMM(95))); sh.SetWidth(FromMM(0.1)); board.Add(sh)
def slot(x1,y1,x2,y2):
    s=pcbnew.PCB_SHAPE(board); s.SetShape(pcbnew.SHAPE_T_RECT); s.SetLayer(pcbnew.Edge_Cuts)
    s.SetStart(VECTOR2I(FromMM(x1),FromMM(y1))); s.SetEnd(VECTOR2I(FromMM(x2),FromMM(y2))); s.SetWidth(FromMM(0.1)); board.Add(s)
for x in [32,49,66,83]: slot(x-8,32.5,x+8,33.5)
slot(93,51.5,137,52.5)
ok=pcbnew.ImportSpecctraSES(board, SES); print("ses import:", ok)
pcbnew.SaveBoard(B, board)
# text pass: drop every MAINS_L / MAINS_N segment and via the router or the export round-trip left behind
s=open(B).read()
def strip(s, kind):
    out=[]; i=0; n=0
    while True:
        j=s.find("\n\t("+kind, i)
        if j<0: out.append(s[i:]); break
        out.append(s[i:j])
        k=j+1; depth=0
        while True:
            c=s[k]
            if c=="(": depth+=1
            elif c==")":
                depth-=1
                if depth==0: k+=1; break
            k+=1
        blk=s[j:k]
        if any(('(net "/Mains IO/%s")' % nn) in blk for nn in ["MAINS_L","MAINS_N","DEMAND_RET","COM1","COM2","COM3","COM4","NO1","NO2","NO3","NO4"]): n+=1
        else: out.append(blk)
        i=k
    return "".join(out), n
s,n1=strip(s,"segment"); s,n2=strip(s,"via"); open(B,"w").write(s); print("stripped L/N segments:",n1,"vias:",n2)
board=pcbnew.LoadBoard(B)
for z in list(board.Zones()):
    if z.GetZoneName().startswith("MAINS_BUS_CORRIDOR") or z.GetZoneName().startswith("EDGE_GUARD") or z.GetZoneName()=="LDO_POUR_KEEPOUT": board.Remove(z)
L="/Mains IO/MAINS_L"; N="/Mains IO/MAINS_N"
def track(net, layer, x1,y1,x2,y2, w=2.5):
    t=pcbnew.PCB_TRACK(board); t.SetStart(VECTOR2I(FromMM(x1),FromMM(y1))); t.SetEnd(VECTOR2I(FromMM(x2),FromMM(y2)))
    t.SetWidth(FromMM(w)); t.SetLayer(layer); t.SetNet(board.FindNet(net)); board.Add(t)
def via(net, x,y, d=1.6, drill=0.8):
    v=pcbnew.PCB_VIA(board); v.SetPosition(VECTOR2I(FromMM(x),FromMM(y))); v.SetWidth(FromMM(d)); v.SetDrill(FromMM(drill))
    v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu); v.SetNet(board.FindNet(net)); board.Add(v)
def buses():
    # L bus nearest the terminals (y 12.5) so its drops to J111..J114 pin 1 never cross N; N bus at y 17
    track(L,pcbnew.F_Cu,14.5,8,14.5,12.5); track(L,pcbnew.F_Cu,14.5,12.5,131,12.5)
    for x in [27,44,61,78]: track(L,pcbnew.F_Cu,x,12.5,x,8)
    via(L,130.6,12.5,1.2,0.6); track(L,pcbnew.B_Cu,130.6,12.5,130.6,23.2,2.0); via(L,130.6,23.2,1.2,0.6); track(L,pcbnew.F_Cu,130.6,23.2,131,24.3,2.0)
    track(N,pcbnew.B_Cu,19.5,8,19.5,17); via(N,19.5,17); track(N,pcbnew.F_Cu,19.5,17,135,17)
    for x in [99,108,117,135]:
        via(N,x,17); track(N,pcbnew.B_Cu,x,17,x,23.2); via(N,x,23.2); track(N,pcbnew.F_Cu,x,23.2,x,24.3,2.0)
buses()
# relay contacts + DEMAND_RET, fixed so the router works around them
def contacts_and_demand():
    for n,xt in enumerate([32,49,66,83], start=1):
        for net,xp,xr in [(f"/Mains IO/COM{n}",xt,xt-2.55),(f"/Mains IO/NO{n}",xt+5,xt+3.8)]:
            track(net,pcbnew.B_Cu,xp,8,xp,19); track(net,pcbnew.B_Cu,xp,19,xr,25.38)
    DR="/Mains IO/DEMAND_RET"
    track(DR,pcbnew.B_Cu,143.5,25,140.5,28,2.0); track(DR,pcbnew.B_Cu,140.5,28,126,28,2.0); track(DR,pcbnew.B_Cu,126,28,126,23.2,2.0)   # sense-chain return only: 2.0 mm, leaves room for the DEMAND_230 lane
    via(DR,126,23.2); track(DR,pcbnew.F_Cu,126,23.2,126,24.3,2.0)
contacts_and_demand()
selv=[(0,39),(88.5,39),(88.5,55.5),(150,55.5),(150,95),(0,95)]
def pour(layer, net, prio):
    z=pcbnew.ZONE(board); z.SetLayer(layer); z.SetNet(board.FindNet(net)); z.SetZoneName(f"{net}_{board.GetLayerName(layer)}")
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL); z.SetMinThickness(FromMM(0.25)); z.SetLocalClearance(FromMM(0.3)); z.SetAssignedPriority(prio); z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
    for x,y in selv: z.AppendCorner(VECTOR2I(FromMM(x),FromMM(y)), -1, False)
    board.Add(z)
pour(pcbnew.F_Cu,"GND",1); pour(pcbnew.B_Cu,"GND",0)
# +3V3 heat-spreading copper on the AMS1117 tab (SOT-223 tab = pin 2 = 3V3); the area was a routing keepout, so it fills whole
z=pcbnew.ZONE(board); z.SetLayer(pcbnew.F_Cu); z.SetNet(board.FindNet("+3V3")); z.SetZoneName("3V3_LDO_TAB")
z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL); z.SetMinThickness(FromMM(0.25)); z.SetLocalClearance(FromMM(0.3)); z.SetAssignedPriority(5); z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
for x,y in [(53.3,66.5),(62.6,66.5),(62.6,79.8),(60.0,79.8),(60.0,84.5),(55.0,84.5),(55.0,79.8),(53.3,79.8)]: z.AppendCorner(VECTOR2I(FromMM(x),FromMM(y)), -1, False)
board.Add(z)
pcbnew.ZONE_FILLER(board).Fill(board.Zones())
# a stitching via whose GND island on each layer holds no GND pad connects nothing: drop it so island removal clears the copper
gnd=board.FindNet("GND").GetNetCode()
pads=[(p.GetPosition(), p.GetLayerSet()) for f in board.Footprints() for p in f.Pads() if p.GetNetCode()==gnd]
def island_has_pad(z, layer, pt):
    polys=z.GetFilledPolysList(layer)
    for i in range(polys.OutlineCount()):
        o=polys.Outline(i)
        if o.PointInside(pt):
            return any(o.PointInside(pp) for pp,ls in pads if ls.Contains(layer))
    return True   # not in any island: leave the via alone
zF=[z for z in board.Zones() if z.GetZoneName()=="GND_F.Cu"][0]; zB=[z for z in board.Zones() if z.GetZoneName()=="GND_B.Cu"][0]
drop=[t for t in board.GetTracks() if t.GetClass()=="PCB_VIA" and t.GetNetCode()==gnd and not island_has_pad(zF,pcbnew.F_Cu,t.GetPosition()) and not island_has_pad(zB,pcbnew.B_Cu,t.GetPosition())]
for v in drop: board.Remove(v)
if drop: pcbnew.ZONE_FILLER(board).Fill(board.Zones())
print("floating stitching vias removed:", len(drop))
# GND islands that hold pads but are cut off from the main pour: add a via where the other layer's main pour lies underneath
def repair_islands():
    added=0
    holes=[t.GetPosition() for t in board.GetTracks() if t.GetClass()=="PCB_VIA"]+[p.GetPosition() for f in board.Footprints() for p in f.Pads() if p.GetDrillSize().x>0]
    for layer,other in ((pcbnew.F_Cu,pcbnew.B_Cu),(pcbnew.B_Cu,pcbnew.F_Cu)):
        zl=zF if layer==pcbnew.F_Cu else zB; zo=zF if other==pcbnew.F_Cu else zB
        pl=zl.GetFilledPolysList(layer); po=zo.GetFilledPolysList(other)
        if pl.OutlineCount()<2 or po.OutlineCount()<1: continue
        main_o=max(range(po.OutlineCount()), key=lambda i: po.Outline(i).Area()); mo=po.Outline(main_o)
        main_l=max(range(pl.OutlineCount()), key=lambda i: pl.Outline(i).Area())
        for i in range(pl.OutlineCount()):
            if i==main_l: continue
            o=pl.Outline(i)
            if not any(ls.Contains(layer) and o.PointInside(pt) for pp,ls in pads for pt in [pp]): continue
            bb=o.BBox(); best=None
            x=bb.GetLeft()+FromMM(0.5)
            while x<bb.GetRight() and best is None:
                y=bb.GetTop()+FromMM(0.5)
                while y<bb.GetBottom():
                    pts=[VECTOR2I(x+dx,y+dy) for dx,dy in ((0,0),(FromMM(0.8),0),(-FromMM(0.8),0),(0,FromMM(0.8)),(0,-FromMM(0.8)))]
                    clear=all((h.x-x)**2+(h.y-y)**2 >= FromMM(1.4)**2 for h in holes)   # never on top of another drill
                    if clear and all(o.PointInside(p) for p in pts) and all(mo.PointInside(p) for p in pts): best=VECTOR2I(x,y); break
                    y+=FromMM(0.5)
                x+=FromMM(0.5)
            if best is not None:
                v=pcbnew.PCB_VIA(board); v.SetPosition(best); v.SetWidth(FromMM(0.8)); v.SetDrill(FromMM(0.4)); v.SetLayerPair(pcbnew.F_Cu,pcbnew.B_Cu); v.SetNet(board.FindNet("GND")); board.Add(v); added+=1
    return added
n=repair_islands(); print("island repair vias:", n)   # one pass: a connected island still shows as its own outline
if n: pcbnew.ZONE_FILLER(board).Fill(board.Zones())
pcbnew.SaveBoard(B, board); print("saved; zones:", len(board.Zones()))
