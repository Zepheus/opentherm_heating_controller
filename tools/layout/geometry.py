"""Board geometry shared by placement, pre-routing, routing, silkscreen and checks. Change it here, nowhere else.

Coordinates in mm, origin at the board's top-left corner, y down. The board hangs on a wall with the field cables
coming in from below: relay and OpenTherm terminals on the bottom edge, USB-C, probe terminals and Qwiic on the left
edge, no wiring from the top or right edge (the module's antenna faces the top edge).
"""
W, H = 160.0, 95.0

# ---- mains strip along the bottom: four TE RT1 (RT314005) changeover relays lying horizontally, coil end left,
#      contacts right. Datasheet drawing S0418-CA: coil 20.3 mm from COM, contacts 5.04 mm pitch, rows 7.5 mm apart
RX = [30.0, 64.0, 98.0, 132.0]      # relay centres; 34 mm pitch keeps 6.8 mm between neighbouring channels
RY = 71.5
PIN_DY = 3.75                       # each contact is a pair of pins at RY -/+ 3.75 (internally the same contact)
COIL_DX = -12.67                    # coil pins at RX - 12.67
COL_DX = {"NC": 2.59, "COM": 7.63, "NO": 12.67}  # contact columns 12, 11, 14, nearest the coil first
TERM_Y = 87.0                       # terminal pin row, wire entries facing the bottom edge; pin 1 NC, 2 COM, 3 NO
TERM_CX = 7.63                      # terminal footprint origin (pin 2, COM) on the relay COM column
TERM_DX = {"NC": TERM_CX - 5.0, "COM": TERM_CX, "NO": TERM_CX + 5.0}   # 5.0 mm terminal pitch vs 5.04 mm contact pitch
LINK_W = 2.5                        # contact-to-terminal copper
CONTACT_TOP = RY - PIN_DY - 1.0     # top edge of the upper contact pads (66.75)

def contact_net(n, c): return f"/Relays/{c}{n}"

def channel_zone(xr):
    """Contact copper of one channel down to the bottom edge (temporary routing keep-out)."""
    return [(xr - 5.0, CONTACT_TOP - 0.3), (xr + 20.0, CONTACT_TOP - 0.3), (xr + 20.0, H), (xr - 5.0, H)]

def isolation_band(xr):
    """6.4 mm above the contacts: nothing in it, ever. Low-voltage copper stays above it."""
    return [(xr - 5.0, CONTACT_TOP - 6.6), (xr + 20.0, CONTACT_TOP - 6.6), (xr + 20.0, CONTACT_TOP - 0.3), (xr - 5.0, CONTACT_TOP - 0.3)]

def slots(xr):
    """1.0 mm routed slots: inside the relay between coil and contacts, and between this channel and the next."""
    s = [(xr - 5.5, RY - 7.5, xr - 4.5, RY + 7.5)]
    if xr != RX[-1]: s.append((xr + 16.6, RY - 7.5, xr + 17.6, H - 1.5))
    return s

RAIL_Y = 50.0                       # +5V rail above the driver row (F.Cu), feeding every coil and driver
RAIL_X = (17.8, RX[-1] + COIL_DX + 5.0)   # starts at the B.Cu feed from the USB receptacle
RAIL_W = 1.0
COIL_DROP_DX = 3.5                  # B.Cu drop from the rail to coil pin 1 (+5V), right of the coil column
# ---- OLED: a 1.3" SH1106 (35.4 x 33.5 mm) or 0.96" SSD1306 module sits in the cover window on a short cable from J5,
#      a Qwiic (JST-SH 4-pin) socket at the top of OLED_BOX with its opening facing down into the box; the box stays
#      empty so the module's back and cable have room under the cover (sanity check)
OLED_CONN = (118.7, 11.5)           # J5 centre; courtyard 8.2 mm from the top edge; pin 1 (GND) on the left
OLED_BOX = (101.0, 10.3, 136.4, 43.8)       # reserved, kept clear of parts (J5 excepted)
SELV_BOTTOM = CONTACT_TOP - 6.6     # GND pours stay above this line (60.1)
ANTENNA = [(14.0, 0.0), (40.0, 0.0), (40.0, 7.0), (14.0, 7.0)]   # module antenna end at the top edge, plus margin, stopping short of its pads (7.6)

# ---- connectors: every external connector sits at a board edge with its cable entry facing out, so enclosure
# cutouts reach it. All these footprints have their entry on local +y; at rotation r it faces (sin r, cos r).
EDGE_CONNECTORS = {
    "J111": ("bottom", 0), "J112": ("bottom", 0), "J113": ("bottom", 0), "J114": ("bottom", 0),   # relay outputs
    "J201": ("bottom", 0),                                                                         # OpenTherm
    "J1": ("left", 270), "J6": ("left", 270), "J3": ("left", 270), "J4": ("left", 270),           # USB-C, Qwiic, probes
}
NO_CABLE_EDGES = ("top", "right")   # no connector may face these edges
EDGE_MAX_GAP = 3.0                  # courtyard to its edge, mm
# internal headers (cables stay inside the enclosure): far enough from every edge to plug a housing in from any side
INTERNAL_HEADERS = {"J5": 8.0, "J7": 8.0}   # OLED, spare GPIO: minimum distance to any edge, mm
