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
for d in list(board.GetDrawings()):
    if d.GetClass() == "PCB_TEXT" and d.GetLayer() in (pcbnew.F_SilkS, pcbnew.B_SilkS):
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
def pin_labels(ref, names, dy=-2.4, size=0.8):
    for i, n in enumerate(names, start=1):
        if n: x, y = PAD[(ref, str(i))]; text(n, x, y + dy, size)

# ---- relay channels: "CHn  NC  COM  NO" in the strip between each terminal block and its relay
label_y = (BOX["J111"][3] + BOX["K101"][1]) / 2
for n, xr in enumerate(G.RX, start=1):
    for c, dx in G.TERM_DX.items(): text(c, xr + dx, label_y, 1.0)
    text(f"CH{n}", xr - 1.6, label_y, 1.2, h="r")
for i, line in enumerate(["RELAY OUTPUTS: VOLT-FREE", "250VAC 3A MAX", "ISOLATE BEFORE OPENING"]):
    text(line, 10.5, 9.6 + i * 1.3, 0.8)

# ---- low-voltage connectors
above("J201", "OPENTHERM")
x0, y0, x1, y1 = BOX["J3"]; text("FLOW TEMP", (x0 + x1) / 2, y0 - 3.3); pin_labels("J3", ["3V3", "DAT", "GND"])
x0, y0, x1, y1 = BOX["J4"]; text("OUTDOOR TEMP", (x0 + x1) / 2, y0 - 3.3); pin_labels("J4", ["3V3", "DAT", "GND"])
x0, y0, x1, y1 = BOX["J1"]; text("USB-C 5V >=1A", x1 + 0.8, (y0 + y1) / 2 + 1.5, 0.8, h="l")
x0, y0, x1, y1 = BOX["J6"]; text("QWIIC I2C", (x0 + x1) / 2, y1 + 0.9, 0.8)
pin_labels("J5", ["GND", "3V3", "SCL", "SDA"], dy=2.4); above("J5", "OLED")
pin_labels("J7", ["16", "17", "10", "11", "18", "19", "3V3", "GND"]); x0, y0, x1, y1 = BOX["J7"]; text("SPARE GPIO", (x0 + x1) / 2, y0 - 3.3)
above("J8", "BOOT JP")
for ref, s in [("SW1", "RESET"), ("SW2", "BOOT"), ("SW3", "BTN1"), ("SW4", "BTN2")]: above(ref, s)
x0, y0, x1, y1 = BOX["LED1"]; text("STATUS", x0 - 0.5, (y0 + y1) / 2, 0.8, h="r")
x0, y0, x1, y1 = BOX["LED2"]; text("OT", x0 - 0.5, (y0 + y1) / 2, 0.8, h="r")


# ---- identity
text("ANDIRON v1.0", 16.5, 79.5, 1.5)
text("Cedric Van Goethem 2026", 16.5, 81.8, 0.8)

pcbnew.SaveBoard(B, board)
print("silkscreen stage done")
