"""Silkscreen stage: plain-language labels at every connector, channel names, area titles, warnings, identity.

Positions are derived from the footprints (and tools/layout/geometry.py), so labels follow the parts when placement
changes. Idempotent: all board-level text on F.SilkS / B.SilkS is removed first. Reference designators are untouched.
usage: <kicad python> -I silk.py <project_dir>
"""
import sys, os, importlib.util, pcbnew
from pcbnew import FromMM, VECTOR2I
_spec = importlib.util.spec_from_file_location("geometry", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "layout", "geometry.py"))
G = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(G)

P = sys.argv[1]; B = P + "/heating-controller.kicad_pcb"
board = pcbnew.LoadBoard(B)
mm = lambda v: v / 1e6
# footprint data first (proxies go stale after edits in this process)
BOX, PAD = {}, {}
for f in board.Footprints():
    c = f.GetCourtyard(pcbnew.F_CrtYd); bb = c.BBox() if c.OutlineCount() else f.GetBoundingBox(False, False)
    BOX[f.GetReference()] = (mm(bb.GetLeft()), mm(bb.GetTop()), mm(bb.GetRight()), mm(bb.GetBottom()))
    for p in f.Pads():
        if p.GetNumber(): PAD[(f.GetReference(), p.GetNumber())] = (mm(p.GetPosition().x), mm(p.GetPosition().y))
# reference designators (edited first: footprint proxies go stale once the board changes): hidden where a plain-language label names the part; moved where a label needs the space
LABELLED = ["J1", "J3", "J4", "J5", "J6", "J7", "J201", "J111", "J112", "J113", "J114", "SW1", "SW2", "SW3", "SW4"]
FP = {f.GetReference(): f for f in board.Footprints()}
def ref_at(ref, x, y, rot):
    r = FP[ref].Reference(); r.SetPosition(VECTOR2I(FromMM(x), FromMM(y))); r.SetTextAngleDegrees(rot)
for ref in LABELLED: FP[ref].Reference().SetVisible(False)
for ref in ("R1", "R2"):   # to the module side, clear of the USB label
    x0, y0, x1, y1 = BOX[ref]; ref_at(ref, x1 + 0.7, (y0 + y1) / 2, 90)
x0, y0, x1, y1 = BOX["U3"]; ref_at("U3", x1 + 0.7, (y0 + y1) / 2, 90)

for d in list(board.GetDrawings()):
    if d.GetClass() in ("PCB_TEXT", "PCB_SHAPE") and d.GetLayer() in (pcbnew.F_SilkS, pcbnew.B_SilkS):
        board.Remove(d)

def text(s, x, y, size=0.8, rot=0, layer=pcbnew.F_SilkS, h="c"):
    t = pcbnew.PCB_TEXT(board); t.SetText(s); t.SetLayer(layer)
    t.SetPosition(VECTOR2I(FromMM(x), FromMM(y)))
    t.SetTextSize(VECTOR2I(FromMM(size), FromMM(size))); t.SetTextThickness(FromMM(round(size * 0.15, 2)))
    t.SetTextAngleDegrees(rot)
    t.SetHorizJustify({"c": pcbnew.GR_TEXT_H_ALIGN_CENTER, "l": pcbnew.GR_TEXT_H_ALIGN_LEFT, "r": pcbnew.GR_TEXT_H_ALIGN_RIGHT}[h])
    t.SetVertJustify(pcbnew.GR_TEXT_V_ALIGN_CENTER)
    if layer == pcbnew.B_SilkS: t.SetMirrored(True)
    board.Add(t); return t
def above(ref, s, size=0.8, gap=0.9):
    x0, y0, x1, y1 = BOX[ref]; text(s, (x0 + x1) / 2, y0 - gap, size)
def pin_labels(ref, names, dy=-2.4, size=0.8, dx=0.0, h="c"):
    for i, n in enumerate(names, start=1):
        if n: x, y = PAD[(ref, str(i))]; text(n, x + dx, y + dy, size, h=h)

# ---- relay channels: "CHn  NC  COM  NO" in the strip between each relay and its terminal block below
label_y = (BOX["K101"][3] + BOX["J111"][1]) / 2
for n, xr in enumerate(G.RX, start=1):
    for c, dx in G.TERM_DX.items(): text(c, xr + dx, label_y, 1.0)
    text(f"CH{n}", xr - 1.6, label_y, 1.2, h="r")
for i, line in enumerate(["RELAY OUTPUTS: VOLT-FREE", "250VAC 3A MAX PER CHANNEL", "ISOLATE BEFORE OPENING"]):
    text(line, 118.7, 45.2 + i * 1.3, 0.9)   # just above the relay strip, below the OLED

# ---- bottom edge: OpenTherm
x0, y0, x1, y1 = BOX["J201"]; text("OPENTHERM", x1 + 0.6, (y0 + y1) / 2, 0.8, h="l")
for pin, lab in (("1", "OT1"), ("2", "OT2")):
    x, y = PAD[("J201", pin)]; text(lab, x, y0 - 0.9, 0.8)

# ---- left edge: entries face the edge, labels sit beside each connector on the board side
def side_labels(ref, title, pins, title_x):
    x0, y0, x1, y1 = BOX[ref]
    for i, n in enumerate(pins, start=1):
        x, y = PAD[(ref, str(i))]; text(n, x1 + 0.4, y, 0.8, h="l")
    text(title, title_x, (y0 + y1) / 2, 0.9, rot=90)
side_labels("J3", "FLOW", ["3V3", "DAT", "GND"], 12.4)
side_labels("J4", "OUTDOOR", ["3V3", "DAT", "GND"], 12.4)
x0, y0, x1, y1 = BOX["J1"]; text("USB-C 5V >=1A", x1 + 0.55, (y0 + y1) / 2, 0.8, rot=90)
x0, y0, x1, y1 = BOX["J6"]; text("QWIIC", x1 + 0.9, (y0 + y1) / 2, 0.8, rot=90)

# ---- internal headers and controls
x, y = PAD[("J5", "1")]; text("GND", x - 0.9, y, 0.8, h="r")   # pin 1 of the OLED Qwiic socket (GND, 3V3, SDA, SCL)
x0, y0, x1, y1 = BOX["J5"]; text("OLED QWIIC", x1 + 0.6, (y0 + y1) / 2, 0.8, h="l")
x0, y0, x1, y1 = G.OLED_BOX
ol = pcbnew.PCB_SHAPE(board); ol.SetShape(pcbnew.SHAPE_T_RECT); ol.SetLayer(pcbnew.F_SilkS); ol.SetWidth(FromMM(0.15))
ol.SetStart(VECTOR2I(FromMM(x0), FromMM(y0))); ol.SetEnd(VECTOR2I(FromMM(x1), FromMM(y1))); board.Add(ol)
text("OLED MODULE", (x0 + x1) / 2, (y0 + y1) / 2 + 3, 1.0)
pin_labels("J7", ["16", "17", "10", "11", "18", "19", "3V3", "GND"], dy=0, dx=2.0, h="l"); x0, y0, x1, y1 = BOX["J7"]; text("SPARE GPIO", (x0 + x1) / 2 + 1.5, y0 - 0.9)
for ref, s_ in [("SW1", "RESET"), ("SW2", "BOOT"), ("SW3", "BTN1"), ("SW4", "BTN2")]:
    x0, y0, x1, y1 = BOX[ref]; text(s_, (x0 + x1) / 2, y1 + 1.6, 0.8)
x0, y0, x1, y1 = BOX["R9"]; text("STATUS", x1 + 0.5, (y0 + y1) / 2, 0.8, h="l")
x0, y0, x1, y1 = BOX["R11"]; text("OT", x1 + 0.5, (y0 + y1) / 2, 0.8, h="l")

# ---- identity
text("ANDIRON v1.0", 148.0, 14.0, 1.5)
text("Cedric Van Goethem 2026", 148.0, 16.4, 0.8)

pcbnew.SaveBoard(B, board)
print("silkscreen stage done")
