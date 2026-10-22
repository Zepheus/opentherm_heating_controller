# Andiron — design brief (v1.0, 2026-10-22)

An isolated I/O board for a UK heating wiring centre, on WiFi, designed for an
ESPHome firmware. Schedules, thermostats and weather compensation live in Home
Assistant; radiator valves and room sensors are integrated there separately.
The firmware will be written once the first boards are in hand.

Target: KiCad 10, JLCPCB economic assembly, 3D-printed enclosure later.

## What the board does

- **Four volt-free changeover relays** (CH1–CH4): COM, NO and NC on a 3-way
  terminal each. NO switches a zone valve or closes a boiler's demand loop; NC
  provides the "hot water off" signal for a Y-plan mid-position valve. The
  wiring centre supplies its own fused live to COM when a channel must switch
  live. This is how common UK heating controllers present their outputs.
- **OpenTherm master** to the boiler, opto-isolated, fused against a 230 V
  miswire.
- **Two 1-Wire probe inputs** (flow and outdoor), a Qwiic socket, an OLED
  header, two buttons, status LEDs, and an 8-pin spare GPIO header.
- **USB-C** for power (5 V ≥1 A brick) and programming.

The only mains voltage on the board is on the relay contacts. There is no
mains supply input and no mains sensing.

## Safety framing

Per IEC 60730-1 this is a Type 1 (non-safety) control: the boiler's own limit
stat, flame supervision and gas valve are the life-safety layer, and the
boiler interlock lives in the wiring centre's wiring as it does today.
"Fail-safe" for this board means:

1. The board cannot itself cause fire or shock: reinforced isolation between
   every relay channel and everything else, slots in the board, enclosure.
2. A dead, held-in-reset, bootloading or brown-out board leaves every relay
   off (gate pull-downs, GPIOs high-impedance), without firmware involvement.
   A crashed firmware reaches the same state after the ESP-IDF watchdog
   resets the chip (5 s default in ESPHome). Loss of WiFi or Home Assistant
   does not release GPIOs; the firmware switches every relay and OT CH-enable
   off after 30 min without the Home Assistant heartbeat and never restores
   outputs at boot.
3. Residual modes hardware does not clear: a GPIO held on by faulty firmware
   logic, a shorted driver MOSFET, welded contacts. That channel stays on and
   the boiler runs under its own limit thermostat, as with a stuck relay in
   any wiring centre.

## Decisions

| Topic | Decision | Why |
|---|---|---|
| MCU | ESP32-C6-WROOM-1-N8 (PCB antenna), antenna end at the top board edge | Enough GPIO, native USB-Serial-JTAG, ESPHome support. The antenna faces an edge with nothing metallic near it; the module's own antenna is sufficient (the -1U external-antenna variant uses the same footprint if ever needed, but JLCPCB does not stock it) |
| Relays | 4 × TE RT1 RT314005 (C7065270): 1 Form C, 16 A 250 VAC AgNi, 5 V coil 403 mW (62 Ω, 80 mA), 5 mm pinning | Changeover contacts like commercial controllers. Datasheet: 5 kV coil-to-contact, clearance/creepage ≥10/10 mm, reinforced insulation, VDE approved. $1.89 against $3.53 for the Hongfa HF115F/005-1ZS3A it replaced (same 29 × 12.7 mm body and pin grid within 0.15 mm). It is the flux-proof (RTII) version: the wash-tight RTD14005 is not stocked, so the assembled board must not be washed after THT soldering. The HF32F changeover version only manages 2.5 kV and was rejected |
| Relay drive | AO3400A low-side, 100 Ω gate, 100 kΩ gate pull-down, 1N4148W flyback, LED from 5 V through 1 kΩ to the drain | Pull-down keeps the relay off whenever the GPIO is high-impedance; the LED shows the real coil state without a GPIO |
| Contacts | No MOV or snubber across contacts | A failed MOV shorts and energises the load permanently |
| Relay terminals | WJ128V-5.0-3P rising-cage clamp (C8270), pin 1 NC, 2 COM, 3 NO | Ferrule-compatible; pins line up with the relay's contact columns so each link is a straight track |
| 3.3 V | ST LDL1117S33R (C435835), SOT-223 | ~0.35 V dropout at 400 mA (3.3 V holds down to ~3.7 V in), stable with ceramic capacitors, 18 V abs-max so the USB surge clamp cannot hurt it. The tab is a normal soldered lead; no exposed pad and no heat-spreading copper needed at ~0.2 W average |
| 5 V | USB VBUS directly to the relay coils and LEDs | The coils pull in at 3.5 V, so even a sagging 4.5 V supply switches them; regulating this rail gains nothing |
| Switching regulator | Not used | Would save ~0.2 W but adds an inductor and a 1.5 MHz switch node beside the antenna and the OpenTherm receiver |
| Power in | HRO TYPE-C-31-M-12 receptacle, 5.1 kΩ Rd on CC1/CC2, SMF5.0A on VBUS, USBLC6-2SC6 on D±, shield via 1 MΩ ∥ 1 nF | A 5 V ≥1 A brick; CC resistors make C-to-C cables work |
| Bulk | 470 µF/16 V on 5 V, 22 µF + 100 nF at the module pin, 10 µF either side of the regulator | Rides out relay pull-in during a WiFi burst; firmware staggers relay pull-in by 100 ms |
| OpenTherm | Ihor Melnyk master adapter: 2 × LTV-817S, S8550 PNP, 1N4148WS bridge, zeners 4V7/15 V/4V3, 1 A 250 V fast 2410 fuse (F201, AEM MF2410F1.000TM, 100 A breaking at 250 V, I²t 0.62 A²s) in series with OT1, SMAJ24A across the bridge output | 230 V on OT1/OT2 drives the bridge into the TVS, which clamps at ≤39 V; the fault current is limited by the fuse and wiring only and the fuse clears in well under a millisecond. Bench fault test through a current-limited source is on the test list. A time-lag 2410 fuse is cheaper still but holds 10 × rated current for ≥10 ms, which the TVS would have to absorb, so only fast-acting parts are acceptable |
| Display | 4-pin header GND / 3V3 / SCL / SDA, SSD1306/SH1106 at 0x3C, 4.7 kΩ pull-ups | The standard pinout of common 0.96" I2C modules; powered at 3.3 V so the module's own pull-ups stay at a level the ESP32 tolerates |
| Sensors | 1-Wire bus, 4.7 kΩ pull-up, 330 Ω series, SMF5.0A TVS on the external node; two 3-pin terminals FLOW and OUTDOOR | Waterproof DS18B20 probes. The series resistor limits clamp current into the MCU pin to ~16 mA during a surge |
| Expansion | Qwiic JST-SH 4-pin; 8-pin spare header (GPIO16, 17, 10, 11, 18, 19, 3V3, GND) | Room for sensors or extra inputs without a board spin |
| Buttons | BTN1 (GPIO4), BTN2 (GPIO5), BOOT (GPIO9) + boot jumper, RESET (EN) | General-purpose buttons for boosts when Home Assistant is down |

## Isolation (DRC-enforced)

IEC 62368-1 / 60730-1, 230 V, OVC II, PD2, material group IIIb assumed:
reinforced 3.0 mm clearance / 5.0 mm creepage. Design floor **6.4 mm** for both.

- Each relay channel's contact nets (NCn, COMn, NOn) form their own net class
  CHn. DRC rule `channel-isolation`: 6.4 mm clearance and creepage from
  anything that is not the same channel: the other channels and every
  low-voltage net. Within a channel: 2.0 mm (functional, across an open contact).
- Contact copper ≥2.0 mm wide (links are 2.5 mm), ≥2.0 mm from the edge.
- 1.0 mm routed slots inside each relay footprint between coil and contacts,
  and between neighbouring channels.
- Isolation band (rule area, nothing allowed) under each channel's contacts;
  low-voltage copper and the GND pours start below it.
- Channel pitch 34 mm gives 6.8 mm between one channel's contacts and the next
  channel's coil pins; the measured minimum creepage on the board is ~8.8 mm
  (DRC flags it when the rule is tightened to 9 mm).
- The limits and their basis are in `tools/check/spacing_rules.json`; the
  sanity check fails if the DRC file stops encoding any of them.
- Low-voltage copper: 0.25 mm clearance (0.2 mm for the USB nets and inside
  the USB-C pad row), so module pins escape straight out.

## GPIO map — ESP32-C6-WROOM-1

Strapping: GPIO8 must be high for download mode (status LED with 10 kΩ
pull-up), GPIO9 low = download (BOOT button/jumper, 10 kΩ pull-up), GPIO15
JTAG select (eFuse default, ignored). GPIO12/13 = USB. GPIO16 prints the ROM
boot log at every reset.

| GPIO | Function |
|---|---|
| 0 | 1-Wire bus (FLOW + OUTDOOR) |
| 1 | OT_IN (RX opto as emitter follower from 3V3, 1.5 kΩ pull-down) |
| 2 | OT_OUT (TX opto LED) |
| 3 | CH4 relay |
| 4 | BTN1 (10 kΩ pull-up, 100 nF) |
| 5 | BTN2 (10 kΩ pull-up, 100 nF) |
| 6 / 7 | I2C SDA / SCL (4.7 kΩ) — OLED and Qwiic |
| 8 | STATUS LED, active-low, 10 kΩ pull-up (strap) |
| 9 | BOOT button + jumper (strap) |
| 10, 11, 18, 19 | spare header |
| 12 / 13 | USB D− / D+ |
| 15 | OT activity LED, active-low, 10 kΩ pull-up |
| 16 / 17 | spare header (U0TXD / U0RXD) |
| 20 | not connected |
| 21 / 22 / 23 | CH1 / CH2 / CH3 relays |
| EN | RESET button, 10 kΩ + 1 µF |

## Power budget

| Load | Rail | Typical | Peak |
|---|---|---|---|
| 4 × relay coils (80 mA each) | 5 V | 160 mA (2 on) | 320 mA |
| ESP32-C6 (WiFi TX bursts) | 3.3 V | ~100 mA | ~380 mA |
| OLED, LEDs, sensors | 3.3 V / 5 V | ~30 mA | ~40 mA |
| **Total from USB** | | **~290 mA** | **~750 mA** |

A 5 V ≥1 A USB-C brick on a short cable is the supported supply. A laptop
USB 2 port (500 mA) is fine for flashing with the relays off; the 470 µF bulk
capacitor's hot-plug inrush may trip some hub ports, in which case power from
the brick and flash over WiFi. Regulator dissipation ~0.2 W average, 0.65 W
during WiFi bursts.

## Layout by area (160 × 95 mm, 2 layers)

The board hangs on a wall with the cables coming from below and from the left
(R11). Nothing is wired from the top or right edge, so the module's antenna
takes the top edge.

| Area | Where | Contents |
|---|---|---|
| Relay strip | bottom, y 60–95 | 4 relays lying horizontally (coil left, NC/COM/NO right), each terminal block below its contacts on the bottom edge, "CHn NC COM NO" labels between relay and terminal |
| Relay drivers | y 51–60, above each coil | MOSFET, gate resistors, flyback diode, LED per channel |
| MCU | top left | module with its antenna at the top edge; decoupling at the 3V3 pin and the EN RC on its left; spare header and boot jumper along its right pin column |
| Left edge | x 0–8 | Qwiic, USB-C, FLOW and OUTDOOR terminals, entries facing out, labels beside them |
| Power | below the module | USB ESD, CC and shield parts at the receptacle, VBUS TVS, bulk capacitor, regulator |
| Sensors | beside the probe terminals | 1-Wire pull-up, series resistor, TVS |
| OpenTherm | bottom-left corner and the row above the drivers | terminal in the corner of the bottom edge with fuse, TVS and bridge next to it; transistor stage and both optos in a row at y 40–48 |
| Controls | right of the module | I2C pull-ups, STATUS and OT LEDs, RESET/BOOT/BTN1/BTN2 buttons and their RC filters |
| OLED | top right, x 101–136, y 10–44 | J5 header along the top of a reserved empty area; a 1.3" SH1106 or 0.96" SSD1306 module stacks on it in landscape and is seen through a window in the cover. Identity text to its right, the relay warning legend below it |

Mounting holes M3 at the four corners; three fiducials in the low-voltage area.
All courtyards inside the outline.

## Routing

The layout is generated from `tools/route/placed.kicad_pcb` by
`tools/route/run_pipeline.sh`; placement lives in `tools/layout/place.py`, the
shared geometry (relay row, terminals, zones, slots, antenna keep-out) in
`tools/layout/geometry.py`. Locked pre-routes: the contact links, the USB-C pad
bridges and VBUS escape, and a GND stitching grid. Freerouting routes the rest
(40 passes, about a minute); the pipeline then pours GND on both layers below
the isolation band, repairs pour islands, removes router leftovers, lays the
silkscreen and runs DRC and the sanity report. What worked and what did not is
recorded in `layout-notes.md`.

## Assembly

All SMD by JLCPCB. Through-hole (relays, terminals, headers, USB shell pins)
by JLC's through-hole service or at home. No QFN/BGA; smallest parts SOT-23
and 0603; only the USB-C receptacle is below 1 mm pitch.

## Enclosure

IEC 60730-1 §21 / 60335-1 §30.2: parts supporting >0.2 A connections must pass
850 °C glow-wire, the rest 650 °C. Owner's choice: print it in a filament with
a vendor UL94 V-0 claim (ABS-FR / PC-FR), ≥2.5 mm walls, no vents above the
relays, screwed lid, warning label "230 V — isolate at fused spur before
opening". A filament's V-0 rating is for the material, not the printed wall.
Buttons sit inside the lid, ≥5 mm from the board edge. The OLED module
stacks on its header over the empty top-right area and shows through a window
in the cover. The four channels need the 160 × 95 mm board, so the enclosure is
about 170 × 105 mm; a three-channel board would fit a common 151 × 94 mm hub
enclosure but was rejected to keep four outputs. Installation: cover off, wire
the screw terminals from below and the left, cover back on. Two-part pluggable
terminals (about $1 per board more, plugs bought separately) were considered
and not adopted.

## History

- **Rev 1–6 (Oct 2026):** first design with a 230 V supply input, L/N rails,
  five opto-isolated mains sensing inputs (valve end switches, boiler demand,
  mains presence) and make-only relays.
- **Independent review (Oct 2026):** found an OpenTherm net merge (TX echoing
  into RX, fixed), missing miswire protection (fuse added), detector margin
  and spacing issues in the sensing circuits.
- **v1.0 (22 Oct 2026):** sensing removed as over-engineering for a home
  install; relays changed to volt-free changeover contacts; regulator changed
  to LDL1117 with no heat-spreading copper; OLED header fixed to the standard
  pinout; layout redone by module area with the antenna at the left edge.
- **v1.0 wall-hanging layout (22 Oct 2026):** board turned for wall mounting
  (160 × 95 mm): all field cables from below or from the left, relay and
  OpenTherm terminals on the bottom edge, USB-C, probes and Qwiic on the left
  edge, antenna at the top edge. Relay terminal pins read NC, COM, NO from
  left to right.

## Open questions

1. Vitodens type code: 100-W and 050-W speak OpenTherm (with the module);
   200-series do not. Behaviour when OT communication stops?
2. S-plan (2 × 2-port valves) or Y-plan (mid-position valve) at the install?
3. Outdoor sensor fitted on the boiler (OT ID 27)?
4. Mounting location and measured temperature there.
