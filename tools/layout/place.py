"""Placement of the Andiron board by module area. Writes positions into tools/route/placed.kicad_pcb.

Areas (board 150 x 90 mm, origin top-left):
  mains strip   y 0-35   four HF115F relays lying horizontally, coil end left, contacts NC/COM/NO right,
                         each with its 3-way terminal directly above the contacts (pins line up with the
                         contact columns, 5.0 vs 5.04 mm pitch); channel pitch 34 mm keeps 6.8 mm between channels
  driver row    y 37-47  each relay's MOSFET, gate resistors, flyback diode and LED under its own coil
  MCU           x 0-30   ESP32-C6 module, antenna facing the left edge, EN/BOOT RC and decoupling at its pins
  power         x 30-62  USB-C on the bottom edge, ESD/TVS/CC at the connector, bulk cap, LDO and its copper
  OpenTherm     x 62-100 terminal on the bottom edge, fuse, bridge, TVS, transistor stage, the two optos
  sensors       x 100-124 FLOW and OUTDOOR 1-Wire terminals on the bottom edge, pull-up, series R, TVS, Qwiic
  UI            x 124-150 buttons, OLED header, spare header, boot jumper, status LEDs
usage: <kicad python> -I tools/layout/place.py <board>
"""
import sys, os, importlib.util, pcbnew
from pcbnew import FromMM, VECTOR2I
_spec = importlib.util.spec_from_file_location("geometry", os.path.join(os.path.dirname(os.path.abspath(__file__)), "geometry.py"))
G = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(G)

B = sys.argv[1]; board = pcbnew.LoadBoard(B)
W, H = G.W, G.H
P = {}
def p(ref, x, y, rot=0): P[ref] = (x, y, rot)

# ---- mains strip
for n, xr in enumerate(G.RX, start=1):
    p(f"K10{n}", xr, G.RY, 90)                   # rotation 90: coil pins left at xr-12.6, contacts NC/COM/NO to the right
    p(f"J11{n}", xr + G.TERM_CX, G.TERM_Y, 0)
    x0 = xr + G.COIL_DX                           # coil column
    # ---- driver row under the coil
    p(f"Q10{n}", x0 - 1.5, 39.5, 0)
    p(f"R1{n}1", x0 - 1.5, 43.5, 0)              # 100 R gate
    p(f"R1{n}2", x0 - 1.5, 46.0, 0)              # 100 k pull-down
    p(f"D10{n}", x0 + 3.2, 39.5, 90)             # flyback
    p(f"LED10{n}", x0 + 6.0, 39.5, 90)
    p(f"R1{n}3", x0 + 6.0, 44.0, 90)             # LED resistor

# ---- MCU area (antenna to the left edge)
p("U1", 16.3, 62.0, 90)                          # antenna end (pins 1/2 side) at the left edge
p("R4", 30.0, 56.0, 0); p("C8", 30.0, 58.5, 0)   # EN pull-up and delay
p("R5", 30.0, 61.0, 0)                            # BOOT pull-up
# decoupling at the module's 3V3 pin is placed by the script below once the pin position is known

# ---- power area
p("J1", 40.0, 85.5, 0)                            # USB-C, receptacle lip at the bottom edge
p("U3", 40.0, 78.0, 0)                            # USB ESD
p("R1", 34.5, 78.0, 90); p("R2", 45.5, 78.0, 90)  # CC pull-downs
p("C1", 32.0, 82.0, 90); p("R3", 30.0, 82.0, 90)  # shield RC
p("D1", 48.5, 80.0, 90)                           # VBUS TVS
p("C2", 39.0, 67.0, 90)                           # 470 uF bulk
p("C3", 46.0, 69.0, 90)
p("U2", 52.0, 70.0, 0)                            # LDO, tab right
p("C4", 59.5, 70.0, 90); p("C5", 59.5, 74.5, 90)

# ---- OpenTherm area
p("J201", 70.0, 84.5, 180)                        # terminal on the bottom edge
p("F201", 70.0, 77.5, 0)
p("D201", 77.0, 75.0, 90); p("D202", 79.5, 75.0, 90); p("D203", 77.0, 80.0, 90); p("D204", 79.5, 80.0, 90)
p("D208", 84.0, 78.0, 90)
p("Q201", 70.0, 68.0, 0); p("R201", 74.0, 67.5, 90)
p("D206", 77.0, 67.5, 90); p("D205", 79.8, 67.5, 90); p("R202", 82.5, 67.5, 90)
p("R203", 85.0, 67.5, 90); p("D207", 87.8, 67.5, 90)
p("U201", 76.0, 57.0, 0); p("U202", 88.0, 57.0, 0)
p("R204", 71.0, 57.0, 90); p("R205", 94.0, 57.0, 90)

# ---- sensors area
p("J3", 106.0, 84.5, 180); p("J4", 118.5, 84.5, 180)
p("R14", 106.0, 73.0, 0); p("R15", 110.5, 73.0, 0); p("D2", 114.5, 73.5, 90)
p("J6", 104.0, 66.0, 0)                           # Qwiic
p("R12", 110.0, 64.5, 0); p("R13", 110.0, 67.0, 0)  # I2C pull-ups

# ---- UI area
p("SW1", 130.0, 84.0, 0); p("SW2", 138.5, 84.0, 0); p("SW3", 138.5, 75.5, 0); p("SW4", 130.0, 75.5, 0)
p("R6", 145.5, 75.5, 90); p("C9", 147.5, 75.5, 90)
p("R7", 125.5, 75.5, 90); p("C10", 123.5, 75.5, 90)
p("J5", 137.0, 66.0, 90)                          # OLED header, horizontal row
p("J7", 116.0, 55.0, 90)                          # spare GPIO header, horizontal row
p("J8", 104.0, 55.0, 90)                          # boot jumper
p("LED1", 127.0, 60.5, 0); p("R8", 127.0, 63.0, 0); p("R9", 131.5, 60.5, 0)
p("LED2", 138.0, 60.5, 0); p("R10", 138.0, 63.0, 0); p("R11", 142.5, 60.5, 0)

# ---- mechanical
p("H1", 4.0, 4.0); p("H2", 146.0, 4.0); p("H3", 4.0, 86.0); p("H4", 146.0, 86.0)
p("FID1", 30.0, 48.5); p("FID2", 146.0, 48.5); p("FID3", 100.0, 48.5)

missing = []
for f in board.Footprints():
    r = f.GetReference()
    if r not in P: missing.append(r); continue
    x, y, rot = P[r]
    f.SetOrientationDegrees(rot); f.SetPosition(VECTOR2I(FromMM(x), FromMM(y)))

# decoupling right at the module's 3V3 pin (pin 2), GND side away from the module
u1 = [f for f in board.Footprints() if f.GetReference() == "U1"][0]
p3 = [p_ for p_ in u1.Pads() if p_.GetNumber() == "2"][0].GetPosition()
x3, y3 = p3.x / 1e6, p3.y / 1e6
for f in board.Footprints():
    if f.GetReference() == "C7": f.SetOrientationDegrees(90); f.SetPosition(VECTOR2I(FromMM(x3), FromMM(y3 + 2.6)))
    if f.GetReference() == "C6": f.SetOrientationDegrees(90); f.SetPosition(VECTOR2I(FromMM(x3 + 2.6), FromMM(y3 + 2.9)))

# board outline
for d in list(board.GetDrawings()):
    if d.GetLayer() == pcbnew.Edge_Cuts: board.Remove(d)
sh = pcbnew.PCB_SHAPE(board); sh.SetShape(pcbnew.SHAPE_T_RECT); sh.SetLayer(pcbnew.Edge_Cuts)
sh.SetStart(VECTOR2I(0, 0)); sh.SetEnd(VECTOR2I(FromMM(W), FromMM(H))); sh.SetWidth(FromMM(0.1)); board.Add(sh)
pcbnew.SaveBoard(B, board)
print("placed", len(P), "| not placed:", missing or "none", f"| U1 3V3 pin at ({x3:.2f}, {y3:.2f})")
