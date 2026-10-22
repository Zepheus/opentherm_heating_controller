"""Board geometry shared by placement, pre-routing, routing and silkscreen. Change it here, nowhere else.

Coordinates in mm, origin at the board's top-left corner, y down.
"""
W, H = 150.0, 90.0

# ---- mains strip: four HF115F changeover relays lying horizontally, coil end left, contacts right
RX = [21.0, 55.0, 89.0, 123.0]      # relay centres; 34 mm pitch keeps 6.8 mm between neighbouring channels
RY = 23.5
PIN_DY = 3.78                       # each contact is a pair of pins at RY -/+ 3.78 (internally the same contact)
COIL_DX = -12.6                     # coil pins at RX - 12.6
COL_DX = {"NC": 2.52, "COM": 7.56, "NO": 12.6}   # contact columns, nearest the coil first (datasheet, 16 A 1 Form C)
TERM_Y = 8.0                        # terminal pin row; terminal pin 1 NC, 2 COM, 3 NO
TERM_DX = {"NC": 2.56, "COM": 7.56, "NO": 12.56}
TERM_CX = 7.56                      # terminal footprint origin (pin 2) relative to RX
LINK_W = 2.5                        # contact-to-terminal copper

def contact_net(n, c): return f"/Relays/{c}{n}"

def channel_zone(xr):
    """Copper area of one channel's contacts plus 6.4 mm, above the isolation band (routing keep-out)."""
    return [(xr - 5.0, 0.0), (xr + 20.0, 0.0), (xr + 20.0, 29.0), (xr - 5.0, 29.0)]

def isolation_band(xr):
    """Below the lowest contact pad (RY + 3.78 + 1.0 = 28.3): nothing in it, ever."""
    return [(xr - 5.0, 29.0), (xr + 20.0, 29.0), (xr + 20.0, 35.0), (xr - 5.0, 35.0)]

def slots(xr):
    """1.0 mm routed slots: inside the relay between coil and contacts, and between this channel and the next."""
    s = [(xr - 5.5, 16.0, xr - 4.5, 31.0)]
    if xr != RX[-1]: s.append((xr + 16.6, 1.5, xr + 17.6, 31.0))
    return s

SELV_TOP = 35.0                     # everything below is low voltage; GND pours start here
ANTENNA = [(0.0, 49.0), (6.9, 49.0), (6.9, 75.0), (0.0, 75.0)]   # module antenna end at the left edge, plus margin; stops short of the end GND pins (x 7.3)
