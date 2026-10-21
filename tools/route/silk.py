"""Silkscreen stage: board-level labels at every terminal pin plus warnings and the revision string.

Idempotent: every board-level text on F.SilkS / B.SilkS is removed first, then the full set is re-added, so the
stage can run after every re-route. Footprint reference designators are left alone.
usage: silk.py <project_dir>
"""
import sys, pcbnew
from pcbnew import FromMM, VECTOR2I

P = sys.argv[1]; B = P + "/heating-controller.kicad_pcb"
board = pcbnew.LoadBoard(B)
for d in list(board.GetDrawings()):
    if d.GetClass() == "PCB_TEXT" and d.GetLayer() in (pcbnew.F_SilkS, pcbnew.B_SilkS):
        board.Remove(d)

def text(s, x, y, size=0.8, rot=0, layer=pcbnew.F_SilkS, thick=None, h="c"):
    t = pcbnew.PCB_TEXT(board); t.SetText(s); t.SetLayer(layer)
    t.SetPosition(VECTOR2I(FromMM(x), FromMM(y)))
    t.SetTextSize(VECTOR2I(FromMM(size), FromMM(size))); t.SetTextThickness(FromMM(thick or round(size * 0.15, 2)))
    t.SetTextAngleDegrees(rot)
    t.SetHorizJustify({"c": pcbnew.GR_TEXT_H_ALIGN_CENTER, "l": pcbnew.GR_TEXT_H_ALIGN_LEFT, "r": pcbnew.GR_TEXT_H_ALIGN_RIGHT}[h])
    t.SetVertJustify(pcbnew.GR_TEXT_V_ALIGN_CENTER)
    board.Add(t); return t

# --- mains edge: terminal pin names just below each block (bodies end at y 13.35), channel names below that
text("L", 14.5, 14.8); text("N (sense)", 19.5, 14.8, h="l")
for n, x in enumerate([32, 49, 66, 83], start=1):
    text("L", x - 5, 14.8); text("COM", x, 14.8); text("NO", x + 5, 14.8)
    text(f"K{n}", x, 16.6, size=1.0)
text("MAINS IN", 17, 16.6, size=1.0)
text("DANGER 230V - ISOLATE SUPPLY BEFORE OPENING", 114, 5.0, size=1.0)
# right edge: J116 (DEMAND) and J115 (END SW), words run vertically beside the block, one per pin
for s, y in [("230V", 15), ("24V", 20), ("RET", 25), ("ES3", 32), ("ES2", 37), ("ES1", 42)]:
    text(s, 137.6, y, size=0.8, rot=90)
text("230V OR 24V, NEVER BOTH", 143.2, 28.5, size=0.8)
text("24V PIN IS LIVE IN 230V MODE", 143.2, 10.8, size=0.8)
text("END SW", 142.5, 46.0, size=0.8)

# --- SELV edge
text("OT 24V MAX", 58, 84.3, size=0.8)
for xs, name in [((73.5, 70, 66.5), "FLOW"), ((85.5, 82, 78.5), "OUTDOOR")]:
    text("3V3", xs[0], 84.4, size=0.8); text("DAT", xs[1], 84.4, size=0.8); text("GND", xs[2], 84.4, size=0.8)
    text(name, xs[1], 83.0, size=0.8)
text("P1 P2 SCL SDA", 108.2, 86.3, size=0.8); text("OLED: P1/P2 SET BY R16-R21", 108.2, 85.0, size=0.8)
text("QWIIC", 98, 87.6, size=0.8)
text("16 17 3V3 GND", 95.8, 78.3, size=0.8); text("SPARE", 95.8, 77.0, size=0.8)
text("BOOT JP", 121.3, 68.8, size=0.8)
for s, x, y in [("RST", 120, 86.2), ("BOOT", 129, 86.2), ("BTN1", 138, 86.2), ("BTN2", 138, 76.2)]:
    text(s, x, y, size=0.8)
text("USB-C 5V 1A", 40, 83.3, size=0.8)
# revision string along the left edge of the SELV region
text("HEATING-CONTROLLER r1 2026-10 github.com/Zepheus/opentherm_heating_controller", 4.0, 66, size=0.9, rot=90)

pcbnew.SaveBoard(B, board)
print("silkscreen texts:", sum(1 for d in board.GetDrawings() if d.GetClass() == "PCB_TEXT"))
