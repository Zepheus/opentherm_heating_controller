"""Placement of the Andiron board by module area. Writes positions and the outline into tools/route/placed.kicad_pcb.

The board hangs on a wall with every field cable coming from below or from the left (geometry.py):
  bottom edge   OpenTherm terminal in the left corner, then the four relay channels: terminal on the edge with its
                entries facing out, relay above it lying on its side (coil left, NC/COM/NO right), driver above the coil
  left edge     Qwiic, USB-C, FLOW and OUTDOOR terminals, entries facing out
  top-left      ESP32-C6 module, antenna at the top edge (no cables there); its left pin column faces the left-edge
                connectors (I2C, EN, buttons, USB), its right column the spare header, BOOT, relay drives and OT_OUT
  below module  power: USB protection at the receptacle, bulk capacitor, regulator; 1-Wire parts at the probe terminals
  bottom-left   OpenTherm field side (fuse, TVS, bridge) next to its terminal; transistor stage and optos in a row
                above the drivers
  right of module  controls: I2C pull-ups, LEDs, buttons and their RC filters
  top-right     the OLED's Qwiic socket over an empty area; the module sits in the cover window on a short cable
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

# ---- relay strip along the bottom edge
for n, xr in enumerate(G.RX, start=1):
    p(f"K10{n}", xr, G.RY, 90)                   # rotation 90: coil pins left at xr-12.6, contacts NC/COM/NO to the right
    p(f"J11{n}", xr + G.TERM_CX, G.TERM_Y, 0)    # pin 1 NC, entries facing the bottom edge
    x0 = xr + G.COIL_DX                           # coil column; the driver sits above the coil
    p(f"Q10{n}", x0 - 1.5, 58.5, 0)
    p(f"R1{n}1", x0 - 1.5, 54.5, 0)              # 100 R gate
    p(f"R1{n}2", x0 - 1.5, 52.0, 0)              # 100 k pull-down
    p(f"D10{n}", x0 + 3.2, 58.5, 90)             # flyback
    p(f"LED10{n}", x0 + 6.0, 58.5, 90)
    p(f"R1{n}3", x0 + 6.0, 54.0, 270)            # LED resistor, +5V pad towards the rail

# ---- MCU: antenna end at the top edge. Pins: left column x U1-8.75, top to bottom 1 GND, 2 3V3, 3 EN, 4 BTN1, 5 BTN2,
# 6 SDA, 7 SCL, 8 1-Wire, 9 OT_IN, 10 STATUS, 11 IO10, 12 IO11, 13/14 USB; right column top to bottom 28 GND, 27 OT_OUT,
# 26 RLY4, 25 IO16, 24 IO17, 23 OT LED, 21-19 RLY3..1, 17 IO19, 16 IO18, 15 BOOT. Pin pitch 1.27, pin 1 at U1y-8.25.
UX, UY = 27.0, 16.3
p("U1", UX, UY, 0)
# C6/C7 at the 3V3 pin are placed below once the pin position is known
p("R4", 13.0, 13.5, 0); p("C8", 13.0, 16.0, 0)    # EN RC beside the EN pin
p("J7", 40.0, 10.0, 0)                            # spare GPIO header, vertical, along the right pin column
p("R5", 34.0, 28.2, 0)                            # BOOT pull-up, under the BOOT pin

# ---- left edge: Qwiic, USB-C, FLOW, OUTDOOR (all but J1 snapped to the edge below)
p("J6", 4.0, 13.0, 270)                           # Qwiic beside the I2C pins
p("J1", 4.5, 24.5, 270)                           # USB-C level with the module's USB pins; shell lip 0.3 mm from the edge
p("J3", 4.0, 36.0, 270); p("J4", 4.0, 49.0, 270)  # FLOW, OUTDOOR
p("R14", 16.0, 39.5, 90); p("R15", 16.0, 43.0, 90); p("D2", 16.0, 47.5, 90)  # 1-Wire pull-up, series R, TVS (x 8-14 left free for labels)

# ---- power, below the module
p("U3", 12.8, 24.5, 90)                           # USB ESD between the receptacle and the module's USB pins
p("R1", 12.5, 19.5, 90); p("R2", 12.5, 29.0, 90)  # CC pull-downs
p("C1", 15.5, 29.0, 90); p("R3", 15.5, 21.0, 90)  # shield RC
p("D1", 16.2, 33.0, 90)                           # VBUS TVS
p("C2", 24.0, 34.0, 0)                            # 470 uF bulk
p("C3", 31.0, 34.0, 90); p("U2", 37.0, 34.0, 0); p("C4", 43.5, 34.0, 90); p("C5", 43.5, 37.3, 0)

# ---- OpenTherm: field side next to the terminal, transistor stage and optos in a row above the drivers and the +5V rail (opto pads reach 5 mm from centre)
p("J201", 14.0, 89.0, 0)
p("F201", 11.5, 78.0, 90); p("D208", 6.0, 78.0, 90)
for ref, x in [("D201", 3.5), ("D202", 6.5), ("D203", 9.5), ("D204", 12.5)]: p(ref, x, 68.5, 90)
p("Q201", 20.0, 42.0, 0); p("R201", 24.5, 42.0, 90)
p("D206", 28.0, 42.0, 90); p("D205", 31.0, 42.0, 90); p("R202", 33.8, 42.0, 90)
p("R203", 36.3, 42.0, 90); p("D207", 39.3, 42.0, 90)
p("U201", 48.5, 42.0, 0); p("R204", 53.0, 39.0, 90); p("U202", 57.5, 42.0, 0); p("R205", 62.5, 42.0, 90)

# ---- controls, right of the module
p("J5", *G.OLED_CONN, 0)                          # OLED Qwiic socket, opening facing down into the OLED area
p("R12", 63.0, 10.0, 0); p("R13", 63.0, 12.5, 0)  # I2C pull-ups
p("LED1", 69.0, 9.0, 0); p("R8", 69.0, 11.5, 0); p("R9", 73.5, 9.0, 0)     # STATUS LED
p("LED2", 69.0, 14.5, 0); p("R10", 69.0, 17.0, 0); p("R11", 73.5, 14.5, 0)   # OT activity LED
for ref, x in [("SW1", 52.0), ("SW2", 59.5), ("SW3", 67.0), ("SW4", 74.5)]: p(ref, x, 22.5, 90)   # RESET BOOT BTN1 BTN2
p("R6", 59.0, 29.5, 0); p("C9", 59.0, 32.0, 0)    # BTN1 RC
p("R7", 66.0, 29.5, 0); p("C10", 66.0, 32.0, 0)   # BTN2 RC

# ---- mechanical
p("H1", 4.0, 4.0); p("H2", W - 4.0, 4.0); p("H3", 4.0, H - 4.0); p("H4", W - 4.0, H - 4.0)
p("FID1", 50.0, 4.0); p("FID2", W - 4.0, 48.0); p("FID3", 92.0, 47.0)

missing = []
for f in board.Footprints():
    r = f.GetReference()
    if r in ("C6", "C7"): continue
    if r not in P: missing.append(r); continue
    x, y, rot = P[r]
    f.SetOrientationDegrees(rot); f.SetPosition(VECTOR2I(FromMM(x), FromMM(y)))

# left-edge connectors: courtyard 0.5 mm from the edge (J1 is placed exactly, its shell lip at 0.3 mm)
for f in board.Footprints():
    r = f.GetReference()
    if r in G.EDGE_CONNECTORS and G.EDGE_CONNECTORS[r][0] == "left" and r != "J1":
        c = f.GetCourtyard(pcbnew.F_CrtYd); bb = c.BBox() if c.OutlineCount() else f.GetBoundingBox(False, False)
        f.Move(VECTOR2I(FromMM(0.5) - bb.GetLeft(), 0))

# decoupling at the module's 3V3 pin (pin 2): C7 in line with the pin, C6 beside it, both clear of the antenna keep-out
u1 = [f for f in board.Footprints() if f.GetReference() == "U1"][0]
p3 = [p_ for p_ in u1.Pads() if p_.GetNumber() == "2"][0].GetPosition()
x3, y3 = p3.x / 1e6, p3.y / 1e6
for f in board.Footprints():
    if f.GetReference() == "C7": f.SetOrientationDegrees(0); f.SetPosition(VECTOR2I(FromMM(x3 - 2.8), FromMM(y3)))
    if f.GetReference() == "C6": f.SetOrientationDegrees(90); f.SetPosition(VECTOR2I(FromMM(x3 - 5.75), FromMM(y3 + 0.2)))

# board outline
for d in list(board.GetDrawings()):
    if d.GetLayer() == pcbnew.Edge_Cuts: board.Remove(d)
sh = pcbnew.PCB_SHAPE(board); sh.SetShape(pcbnew.SHAPE_T_RECT); sh.SetLayer(pcbnew.Edge_Cuts)
sh.SetStart(VECTOR2I(0, 0)); sh.SetEnd(VECTOR2I(FromMM(W), FromMM(H))); sh.SetWidth(FromMM(0.1)); board.Add(sh)
pcbnew.SaveBoard(B, board)
print("placed", len(P) + 2, "| not placed:", missing or "none", f"| U1 3V3 pin at ({x3:.2f}, {y3:.2f})")
