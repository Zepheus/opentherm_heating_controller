"""Headless "Update PCB from schematic": make a board's footprints and pad nets match the schematic netlist.

- footprints whose reference is not in the schematic are removed (board-only parts with references starting
  H or FID are kept);
- new references are loaded from their library and placed at the origin (place them afterwards);
- a reference whose footprint changed is reloaded from the library, keeping position and rotation;
- value, LCSC, Description and Datasheet fields and the DNP attribute follow the schematic;
- every pad gets the net the netlist gives it (pads absent from the netlist get no net).
Verify afterwards with: kicad-cli pcb drc --schematic-parity

usage: <kicad python> -I tools/sync_netlist.py <project_dir> <board.kicad_pcb>
"""
import sys, os, re, subprocess, tempfile, pcbnew

P, B = sys.argv[1], sys.argv[2]
CLI = os.environ.get("KICAD_CLI", "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli")
KICAD_FP = os.environ.get("KICAD_FOOTPRINTS", "/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints")
net_file = os.path.join(tempfile.mkdtemp(), "andiron.net")
subprocess.run([CLI, "sch", "export", "netlist", "-o", net_file, os.path.join(P, "heating-controller.kicad_sch")], capture_output=True)

# --- minimal s-expression reader for the KiCad netlist
tok = re.findall(r'\(|\)|"(?:[^"\\]|\\.)*"|[^\s()"]+', open(net_file).read())
def parse(i):
    out = []
    while i < len(tok):
        t = tok[i]
        if t == "(": sub, i = parse(i + 1); out.append(sub)
        elif t == ")": return out, i + 1
        else: out.append(t.strip('"')); i += 1
    return out, i
root = parse(0)[0][0]
find = lambda n, k: [x for x in n if isinstance(x, list) and x and x[0] == k]
comps = {}
for c in find(find(root, "components")[0], "comp"):
    d = {k[0]: (k[1] if len(k) > 1 else "") for k in c[1:] if isinstance(k, list) and k and isinstance(k[0], str)}
    props = {p[1][1]: p[2][1] for p in find(c, "property") if len(p) > 2 and isinstance(p[2], list)}
    dnp = any(p[1][1] == "dnp" for p in find(c, "property")) or "dnp" in props
    comps[d["ref"]] = dict(value=d.get("value", ""), footprint=d.get("footprint", ""), datasheet=d.get("datasheet", ""),
                           description=d.get("description", ""), lcsc=props.get("LCSC", ""), dnp=dnp)
pad_net = {}
for n in find(find(root, "nets")[0], "net"):
    name = find(n, "name")[0][1]
    for nd in find(n, "node"):
        d = {k[0]: k[1] for k in nd[1:] if isinstance(k, list) and len(k) > 1}
        pad_net[(d["ref"], d["pin"])] = name

def lib_path(nick):
    return os.path.join(P, "lib", "jlc.pretty") if nick == "jlc" else os.path.join(KICAD_FP, nick + ".pretty")

board = pcbnew.LoadBoard(B)
existing = {f.GetReference(): f for f in board.Footprints()}
removed, added, swapped = [], [], []
for ref, f in existing.items():
    if ref not in comps and not ref.startswith(("H", "FID")):
        board.Remove(f); removed.append(ref)
for ref, c in comps.items():
    nick, name = c["footprint"].split(":", 1)
    f = existing.get(ref)
    if f is not None and str(f.GetFPID().GetUniStringLibId()) == c["footprint"]: continue
    nf = pcbnew.FootprintLoad(lib_path(nick), name)
    if nf is None: sys.exit(f"footprint {c['footprint']} for {ref} not found")
    nf.SetFPIDAsString(c["footprint"]); nf.SetReference(ref)
    if f is not None:
        nf.SetPosition(f.GetPosition()); nf.SetOrientation(f.GetOrientation())
        if f.GetLayer() != nf.GetLayer(): nf.Flip(nf.GetPosition(), pcbnew.FLIP_DIRECTION_TOP_BOTTOM)
        board.Remove(f); swapped.append(ref)
    else:
        added.append(ref)
    board.Add(nf)

def set_hidden(f, name, value):
    if not value: return
    f.SetField(name, value)
    for fld in f.GetFields():
        if fld.GetName() == name: fld.SetVisible(False)

nets = {}
def net(name):
    if name not in nets:
        n = board.FindNet(name)
        if n is None: n = pcbnew.NETINFO_ITEM(board, name); board.Add(n)
        nets[name] = n
    return nets[name]
for f in board.Footprints():
    ref = f.GetReference()
    if ref not in comps: continue
    c = comps[ref]
    f.SetValue(c["value"])
    set_hidden(f, "LCSC", c["lcsc"]); set_hidden(f, "Datasheet", c["datasheet"]); set_hidden(f, "Description", c["description"])
    f.SetAttributes((f.GetAttributes() | pcbnew.FP_DNP) if c["dnp"] else (f.GetAttributes() & ~pcbnew.FP_DNP))
    for p in f.Pads():
        n = pad_net.get((ref, p.GetNumber()))
        if n: p.SetNet(net(n))
        else: p.SetNetCode(0)
pcbnew.SaveBoard(B, board)
print(f"sync: {len(comps)} schematic parts; removed {len(removed)}, added {added}, footprint changed {swapped}")
