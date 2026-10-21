"""One-off: apply the review round-2 schematic changes to the placed (unrouted) board file, in place of
"Update PCB from schematic" (the editor cannot be used while the pipeline rewrites the file).
Verified afterwards with: kicad-cli pcb drc --schematic-parity.
usage: <kicad python> -I this.py <board.kicad_pcb> <project_dir>
"""
import sys, re, glob, pcbnew
from pcbnew import FromMM, VECTOR2I
B, P = sys.argv[1], sys.argv[2]
board = pcbnew.LoadBoard(B)

def net(name):
    n = board.FindNet(name)
    if n is None:
        n = pcbnew.NETINFO_ITEM(board, name); board.Add(n)
    return n

# nets created by the schematic edits
for n in ("/OpenTherm/OT_TXE", "/OpenTherm/OT1_IN"): net(n)

pad_nets = {("U201", "3"): "/OpenTherm/OT_TXE", ("D207", "1"): "/OpenTherm/OT_TXE", ("J201", "1"): "/OpenTherm/OT1_IN",
            ("R146", "2"): "/Mains IO/DEMAND_24", ("R147", "1"): "/Mains IO/LEDK4", ("R147", "2"): "/Mains IO/S4_3", ("R148", "1"): "/Mains IO/S4_3",
            ("J115", "1"): "/Mains IO/ES3_IN", ("J115", "3"): "/Mains IO/ES1_IN"}
values = {"R110": "220k", "R120": "220k", "R130": "220k", "R140": "220k", "R150": "220k", "R15": "330", "D208": "SMAJ24A"}

# LCSC / Description / Datasheet per reference, from the schematic sheets (what "Update PCB from schematic" would copy)
fields = {}
for f in glob.glob(P + "/*.kicad_sch"):
    s = open(f).read()
    for m in re.finditer(r'\(property "Reference" "([^"]+)"', s):
        blk = s[m.start(): s.find("\n\t(symbol", m.start()) if s.find("\n\t(symbol", m.start()) > 0 else len(s)]
        d = {}
        for name in ("LCSC", "Description", "Datasheet"):
            l = re.search(r'\(property "%s" "([^"]*)"' % name, blk)
            if l and l.group(1): d[name] = l.group(1)
        if d: fields[m.group(1)] = d

fps = {f.GetReference(): f for f in board.Footprints()}
for (ref, num), name in pad_nets.items():
    done = False
    for p in fps[ref].Pads():
        if p.GetNumber() == num: p.SetNet(net(name)); done = True
    assert done, (ref, num)
for ref, v in values.items(): fps[ref].SetValue(v)
d208 = fps["D208"]; d208.SetAttributes(d208.GetAttributes() & ~pcbnew.FP_DNP)
def set_hidden_field(f, name, value):
    f.SetField(name, value)
    for fld in f.GetFields():
        if fld.GetName() == name: fld.SetVisible(False)
for ref, f in fps.items():
    for name, val in fields.get(ref, {}).items(): set_hidden_field(f, name, val)

# F201: 2410 fuse in series with OT1, placed between the regulator and the sensor terminals
lib = "/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints/Fuse.pretty"
fp = pcbnew.FootprintLoad(lib, "Fuse_Littelfuse-NANO2-451_453"); fp.SetFPIDAsString("Fuse:Fuse_Littelfuse-NANO2-451_453"); fp.SetReference("F201"); fp.SetValue("1A 250V fast")
fp.SetPosition(VECTOR2I(FromMM(64.0), FromMM(82.0))); fp.SetOrientationDegrees(0)
for name, val in fields["F201"].items(): set_hidden_field(fp, name, val)
for p in fp.Pads(): p.SetNet(net({"1": "/OpenTherm/OT1_IN", "2": "/OpenTherm/OT1"}[p.GetNumber()]))
board.Add(fp)
pcbnew.SaveBoard(B, board)
print("nets:", board.GetNetCount(), "footprints:", len(board.Footprints()))
