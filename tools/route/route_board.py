"""Stage 2 of the routing pipeline: restore the outline and cut the isolation slots, import the SES, strip and re-lay
the relay contact copper deterministically, drop the temporary keep-outs, pour GND over the low-voltage area, repair
pour islands, save.
usage: <kicad python> -I route_board.py <project_dir>
"""
import sys, re, os, collections, importlib.util, pcbnew
from pcbnew import FromMM, VECTOR2I
_spec = importlib.util.spec_from_file_location("geometry", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "layout", "geometry.py"))
G = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(G)
P=sys.argv[1]; B=P+"/heating-controller.kicad_pcb"; SES=P+"/fab/route/heating-controller.ses"
PRO=P+"/heating-controller.kicad_pro"
pcbnew.GetSettingsManager().LoadProject(PRO)
board=pcbnew.LoadBoard(B)
for d in list(board.GetDrawings()):
    if d.GetLayer()==pcbnew.Edge_Cuts: board.Remove(d)
sh=pcbnew.PCB_SHAPE(board); sh.SetShape(pcbnew.SHAPE_T_RECT); sh.SetLayer(pcbnew.Edge_Cuts)
sh.SetStart(VECTOR2I(0,0)); sh.SetEnd(VECTOR2I(FromMM(G.W),FromMM(G.H))); sh.SetWidth(FromMM(0.1)); board.Add(sh)
def slot(x1,y1,x2,y2):
    s=pcbnew.PCB_SHAPE(board); s.SetShape(pcbnew.SHAPE_T_RECT); s.SetLayer(pcbnew.Edge_Cuts)
    s.SetStart(VECTOR2I(FromMM(x1),FromMM(y1))); s.SetEnd(VECTOR2I(FromMM(x2),FromMM(y2))); s.SetWidth(FromMM(0.1)); board.Add(s)
for xr in G.RX:
    for sl in G.slots(xr): slot(*sl)
ok=pcbnew.ImportSpecctraSES(board, SES); print("ses import:", ok)
pcbnew.SaveBoard(B, board)
# text pass: drop every relay contact segment and via the export round trip left behind; they are re-laid below
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
        if kind=="zone": drop=bool(re.search(r'\(name "([^"]*_ZONE|EDGE_GUARD[^"]*)"\)', blk))   # temporary routing keep-outs
        else: drop=bool(re.search(r'\(net "/Relays/(NC|COM|NO)\d"\)', blk))
        if drop: n+=1
        else: out.append(blk)
        i=k
    return "".join(out), n
s,n1=strip(s,"segment"); s,n2=strip(s,"via"); s,n3=strip(s,"zone"); open(B,"w").write(s)
print("stripped relay contact segments:",n1,"vias:",n2,"| temporary keep-outs removed:",n3)
board=pcbnew.LoadBoard(B)   # removing many zones through the API leaves the board proxy unusable, hence the text pass
def track(net, layer, x1,y1,x2,y2, w=G.LINK_W):
    t=pcbnew.PCB_TRACK(board); t.SetStart(VECTOR2I(FromMM(x1),FromMM(y1))); t.SetEnd(VECTOR2I(FromMM(x2),FromMM(y2)))
    t.SetWidth(FromMM(w)); t.SetLayer(layer); t.SetNet(board.FindNet(net)); board.Add(t)
for n, xr in enumerate(G.RX, start=1):
    for c, dx in G.COL_DX.items():
        net = G.contact_net(n, c); x = xr + dx
        track(net, pcbnew.F_Cu, x, G.RY + G.PIN_DY, x, G.RY - G.PIN_DY)
        track(net, pcbnew.F_Cu, x, G.RY + G.PIN_DY, xr + G.TERM_DX[c], G.TERM_Y)
# Freerouting necks tracks down near pads and vias, sometimes below the 0.15 mm board minimum: widen those stubs
narrow=[t for t in board.GetTracks() if t.GetClass()=="PCB_TRACK" and t.GetWidth()<FromMM(0.15)]
for t in narrow: t.SetWidth(FromMM(0.15))
print("narrow router stubs widened to 0.15 mm:", len(narrow))
selv=[(0,0),(G.W,0),(G.W,G.SELV_BOTTOM),(0,G.SELV_BOTTOM)]   # low-voltage area above the isolation band
def pour(layer, net, prio):
    z=pcbnew.ZONE(board); z.SetLayer(layer); z.SetNet(board.FindNet(net)); z.SetZoneName(f"{net}_{board.GetLayerName(layer)}")
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL); z.SetMinThickness(FromMM(0.25)); z.SetLocalClearance(FromMM(0.3)); z.SetAssignedPriority(prio); z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
    for x,y in selv: z.AppendCorner(VECTOR2I(FromMM(x),FromMM(y)), -1, False)
    board.Add(z)
pour(pcbnew.F_Cu,"GND",1); pour(pcbnew.B_Cu,"GND",0)
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
# ...unless a track ends on it: Freerouting uses stitching vias as layer changes, and dropping one cuts that route
track_ends={(pt.x,pt.y) for t in board.GetTracks() if t.GetClass()=="PCB_TRACK" and t.GetNetCode()==gnd for pt in (t.GetStart(),t.GetEnd())}
drop=[t for t in board.GetTracks() if t.GetClass()=="PCB_VIA" and t.GetNetCode()==gnd and (t.GetPosition().x,t.GetPosition().y) not in track_ends
      and not island_has_pad(zF,pcbnew.F_Cu,t.GetPosition()) and not island_has_pad(zB,pcbnew.B_Cu,t.GetPosition())]
for v in drop: board.Remove(v)
if drop: pcbnew.ZONE_FILLER(board).Fill(board.Zones())
print("floating stitching vias removed:", len(drop))
# GND islands that hold pads but are cut off from the main pour: add a via where the other layer's main pour lies underneath
other_pads=[]
for f in board.Footprints():
    for p_ in f.Pads():
        if p_.GetNetCode()!=gnd:
            bb=p_.GetBoundingBox(); other_pads.append((bb.GetLeft(),bb.GetTop(),bb.GetRight(),bb.GetBottom()))
def repair_islands():
    added=0
    holes=[t.GetPosition() for t in board.GetTracks() if t.GetClass()=="PCB_VIA"]+[p.GetPosition() for f in board.Footprints() for p in f.Pads() if p.GetDrillSize().x>0]
    for layer,other in ((pcbnew.F_Cu,pcbnew.B_Cu),(pcbnew.B_Cu,pcbnew.F_Cu)):
        zl=zF if layer==pcbnew.F_Cu else zB; zo=zF if other==pcbnew.F_Cu else zB
        pl=zl.GetFilledPolysList(layer); po=zo.GetFilledPolysList(other)
        if pl.OutlineCount()<2 or po.OutlineCount()<1: continue
        main_o=max(range(po.OutlineCount()), key=lambda i: po.Outline(i).Area())
        targets=[po.Outline(main_o)]+[po.Outline(i) for i in range(po.OutlineCount()) if i!=main_o]   # main pour first, then any other island
        main_l=max(range(pl.OutlineCount()), key=lambda i: pl.Outline(i).Area())
        for i in range(pl.OutlineCount()):
            if i==main_l: continue
            o=pl.Outline(i)
            if not any(ls.Contains(layer) and o.PointInside(pt) for pp,ls in pads for pt in [pp]): continue
            best=None
            for tgt_n in (1, len(targets)):
              if best is not None: break
              bb=o.BBox()
              x=bb.GetLeft()+FromMM(0.5)
              while x<bb.GetRight() and best is None:
                  y=bb.GetTop()+FromMM(0.5)
                  while y<bb.GetBottom():
                      pts=[VECTOR2I(x+dx,y+dy) for dx,dy in ((0,0),(FromMM(0.8),0),(-FromMM(0.8),0),(0,FromMM(0.8)),(0,-FromMM(0.8)))]
                      clear=all((h.x-x)**2+(h.y-y)**2 >= FromMM(1.4)**2 for h in holes)   # never on top of another drill
                      clear=clear and not any(bx0-FromMM(0.65)<=x<=bx1+FromMM(0.65) and by0-FromMM(0.65)<=y<=by1+FromMM(0.65) for bx0,by0,bx1,by1 in other_pads)
                      if clear and all(o.PointInside(p) for p in pts) and any(all(mo.PointInside(p) for p in pts) for mo in targets[:tgt_n]): best=VECTOR2I(x,y); break
                      y+=FromMM(0.5)
                  x+=FromMM(0.5)
            if best is not None:
                v=pcbnew.PCB_VIA(board); v.SetPosition(best); v.SetWidth(FromMM(0.8)); v.SetDrill(FromMM(0.4)); v.SetLayerPair(pcbnew.F_Cu,pcbnew.B_Cu); v.SetNet(board.FindNet("GND")); board.Add(v); added+=1
    return added
n=repair_islands(); print("island repair vias:", n)   # one pass: a connected island still shows as its own outline
if n: pcbnew.ZONE_FILLER(board).Fill(board.Zones())
pcbnew.SaveBoard(B, board); print("saved; zones:", len(board.Zones()))
