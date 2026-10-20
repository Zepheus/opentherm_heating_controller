# Heating controller — design brief (rev 6, 2026-10-20 — schematic drawn)

Replaces a Drayton Wiser Heat Hub R. Dumb, isolated I/O board on WiFi running
ESPHome; scheduling, thermostat and weather-compensation logic live in Home
Assistant. Wiser TRVs stay on HA's existing Zigbee coordinator.

Target: KiCad 10, JLCPCB economic assembly, enclosure later (see §Enclosure).

Rev 2 incorporated two independent adversarial reviews (mains safety; firmware
flexibility); items marked ★ changed from rev 1. Rev 3: simplified power path
(Schottky instead of ideal diode), two general-purpose buttons, assembly plan.

## Safety framing

Per IEC 60730-1 this is a Type 1 (non-safety) control: the boiler's own limit
stat, flame supervision and gas valve are the life-safety layer. "Fail-safe"
for this board therefore means:

1. The board can never itself cause fire or shock (isolation, enclosure, fusing).
2. Any board failure — dead, crashed, WiFi-less, stuck output — leaves zone
   valves spring-closed and the boiler with no demand, **without firmware
   involvement**.

(2) is achieved only by the wiring in §Boiler interlock. Do not deviate from it.

## Decisions (locked)

| Topic | Decision | Why |
|---|---|---|
| MCU ★ | ESP32-C6-WROOM-1-N8 (PCB antenna) | C3-MINI-1 has 13 usable GPIO; this design needs 18. C6 gives 19 usable after USB + UART, six real ADC inputs, same ESP-IDF/ESPHome path, native USB-Serial-JTAG. Zigbee radio unused but present |
| Firmware | ESPHome; OTGateway as OT-only fallback | ESPHome `opentherm` verified 2026-10-20 to expose everything needed (§Firmware). OTGateway has no zone/end-switch support so we do not design to its pin defaults |
| Programming | USB-C native USB-Serial-JTAG only; BOOT jumper + button; RESET button. No UART bridge, no UART header | Cable-only flashing and serial console; jumper for hands-free download mode. UART0 pins GPIO16/17 land on the spare header as plain GPIO |
| Power in | USB-C receptacle is the HRO TYPE-C-31-M-12 (C165948) to match KiCad's footprint. **USB-C 5 V only, from an external certified brick (≥1 A). A PD brick supplies 5 V by default via the CC resistors; no PD chip needed. No on-board mains PSU.** | Owner's decision. The brick is the certified mains barrier; the board's mains section is only the relay contacts and the sense inputs |
| 3.3 V | AMS1117-3.3, SOT-223 (Basic part) on ≥100 mm² pour | Rev 5 cost swap. 15 V abs-max Vin, 1 A; 1.1 V dropout is fine from a 5.0 V brick (3.9 V headroom). AP2112K rejected (6 V abs-max, SOT-23-5 thermals) |
| Relays | 4 × HF32FA-G/005-HSL1 footprints, 3 fitted. SPST-NO 10 A 250 VAC, 5 V coil 46 mA, "-G" reinforced (5 kV coil–contact), sealed | CH + HW + spare today; three zones + DHW/pump on a future combi. "-G" suffix confirmed in MPN. Sealed for lint |
| Relay drive | AO3400A low-side, 100 Ω gate series, 100 kΩ gate pull-down, 1N4148W flyback | Pull-down guarantees "off" through reset, bootloader, brownout and crash; C6 GPIOs are high-Z at reset |
| Relay LEDs ★ | 5 V → 1 kΩ → LED → MOSFET drain | Shows real coil state, costs no GPIO |
| Relay commons | Each relay has a 3-way terminal L / COM / NO (J111–J114). Installer links L–COM with a wire loop for switched-live, or leaves it open for volt-free | A solder jumper at 1.3 mm pitch cannot hold 230 V functional isolation when open, so the link lives in the terminal block |
| Contact protection | **None across contacts, no MOV anywhere.** No snubber footprints (26 mA motor load) | MOV across contacts fails short → valve permanently energised, defeats the interlock. V4043 motor is ~26 mA; 10 A AgSnO2 contacts need nothing |
| AC inputs | 5 × LTV-817S opto with anti-parallel 1N4148WS across the LED (half-wave; Basic parts): ES1–3 (valve end switches, J115, return = MAINS_N), DEMAND (J116: separate 230 V and 24 V input pins — the 24 V pin enters the chain after five of the six resistors — plus its own RET pin), MAINS_OK (senses board L, no terminal). Chain: 6 × 22 kΩ 1206 split 3 + 3 around the opto LED (input → 3 R → LED → 3 R → return; DEMAND: 5 + 1 with the 24 V tap before the last input-side resistor) so both LED pins sit ≥ 66 kΩ from mains and the N return runs along the top corridor; ≈132 kΩ, 1.7 mA, 0.07 W and ~420 V impulse per part; 47 kΩ pull-up + 1 µF on the output. Outputs are active-low (`inverted: true`) | Impulse rating: 2.5 kV Cat II across 4 parts = 625 V each, above a generic 1206's ~400 V; six parts fixes it. RC ≥ 20 ms rides through 100 Hz zero crossings |
| OpenTherm | Ihor Melnyk master adapter: 2 × LTV-817S, S8550 PNP, 1N4148WS bridge, zeners 4V7/15 V/4V3; series LED resistor anti-surge 0.5 W; terminals 3.5 mm on the SELV edge, silk "OT — 24 V max" | Bus is boiler-powered SELV (~5–8 V / 15–18 V, 5–9 / 17–23 mA). Fusible resistor so 230 V miswiring chars one part instead of starting a fire |
| USB-C ★ | 16-pin receptacle, 5.1 kΩ Rd on CC1 and CC2, USBLC6-2SC6 on D±, SMF5.0A on VBUS, shield via 1 MΩ ∥ 1 nF | CC resistors are mandatory for C-to-C cables; ESD lands on the C6's USB pins otherwise |
| Bulk | 470 µF/16 V 105 °C SMD electrolytic (RVT1C471M0810, C3341) on 5 V, 22 µF at module, 10 µF each side of LDO. Firmware staggers relay pull-in by 100 ms | 3 coils + WiFi burst ≈ 525 mA; prevents brownout reboot loops |
| Display | 4-pin header, SSD1306/SH1106 I2C @0x3C. Pin 1/2 order and VCC are chosen with 0 Ω resistors: R16 (pin1→GND, fitted) / R17 (pin1→VCC, DNP), R18 (pin2→VCC, fitted) / R19 (pin2→GND, DNP), R20 (VCC=3V3, fitted) / R21 (VCC=5V, DNP). 4.7 kΩ I2C pull-ups on board | Modules ship GND-VCC-SCL-SDA *and* VCC-GND-SCL-SDA. Solder-jumper footprints with a copper bridge trip KiCad 10's shorting check and JLC cannot bridge them; 0 Ω pairs are explicit and assembled |
| Sensors ★ | 1-Wire bus (4.7 kΩ pull-up, 100 Ω series, 5 V TVS): 3-pin terminal "FLOW" + 3-pin terminal "OUTDOOR" | Waterproof stainless DS18B20 probes; outdoor temp is needed for weather compensation unless the Viessmann reports OT ID 27 |
| Expansion ★ | Qwiic/STEMMA-QT JST-SH 4-pin; 4-pin spare header: GPIO16, GPIO17, 3V3, GND | Expander, BME280 or second display later without a board spin |
| Buttons ★ | BTN1 (GPIO4) and BTN2 (GPIO5), general purpose, assigned in ESPHome later (e.g. boost CH 1 h / boost HW 30 min); plus BOOT and RESET | Optionality; household needs heat when HA or WiFi is down |
| Mains copper ★ | ≥2.5 mm tracks (or 2 oz) for L-in and every relay path; WJ128V-5.0 terminals (250 V 20 A); one N terminal silk "N — sense only" | A valve-cable short delivers 200–400 A for ms before the 3 A fuse clears; 1 mm/1 oz chars |

## Boiler interlock (wiring decision) ★

**Option A — adopted.** Conventional S-plan: every valve's orange (end-switch)
wire is paralleled at the wiring centre and feeds the boiler's 230 V demand
input as it does today. One tap from that node goes to board input ES1 ("any
valve open"). The board asserts OT CH-enable only while ES1 is live. If the
board dies, valves spring shut, oranges open, boiler loses demand — no
firmware in the loop. **Do not link out the boiler's switched live.**

Option B (per-valve sensing): each orange to its own ES input, spare relay K4
as a "BOILER SL" output. Fails safe on board death but not on a K4 weld. Kept
possible by the hardware (ES1–3 + K4 footprint); not the default.

Firmware alarm regardless: ES input live for >60 s while its relay is
commanded off → HA notification, refuse CH-enable (stuck MOSFET / weld).

## Isolation and layout rules (DRC-enforced)

IEC 62368-1:2018 / 60730-1, 230 V, OVC II, PD2, FR-4 group IIIb: basic 1.5 mm
clearance / 2.5 mm creepage; **reinforced (mains ↔ SELV) 3.0 mm / 5.0 mm**.
Design floor: **6.4 mm**, 8 mm where free.

- Net class MAINS: 6.4 mm clearance to every other net, vias and pours included.
- No copper pour on the mains side. Mains copper on the top layer only.
- 1.0 mm routed slot under every LTV-814S and between coil and contact pins of
  every relay, extending ≥3 mm past the body each end (opto pad-to-pad is only
  ~5.5 mm; relay coil–contact ~5–6 mm on the footprint).
- Mounting holes ≥6.4 mm from mains copper, or nylon standoffs.
- No silkscreen, test points or fiducials inside the isolation gap.
- All mains terminals on one board edge; USB-C, OT, 1-Wire, OLED, UART, Qwiic
  on the opposite edge. Cable-tie anchors on the mains side; OLED/sensor leads
  routed along the SELV edge.
- A strand escaping a mains screw terminal must not be able to reach SELV
  copper (60730-1 §11.2) — terminals face outward, SELV parts set back.
- PC817s sit SELV-to-SELV (OT bus is SELV from the boiler); their rating is
  not part of the mains barrier. LTV-814S 5 kVrms UL1577 is.
- Module antenna overhangs the board edge in the Espressif keep-out; no copper
  or parts under it; module on the SELV edge, PSU/relays on the mains edge.

## GPIO map — ESP32-C6-WROOM-1 ★

Strapping: GPIO8 (boot mode, must be high for download; also ROM print),
GPIO9 (boot mode, weak pull-up), GPIO15 (JTAG source), GPIO4/5 (SDIO clock
edge only — harmless here). GPIO12/13 = USB. GPIO16/17 = U0TXD/U0RXD (ROM
prints on 16 at every reset). ADC1 on GPIO0–6. GPIO14 not bonded out.

| GPIO | Function | Boot notes |
|---|---|---|
| 0 | 1-Wire bus (FLOW + OUTDOOR terminals) | high-Z at reset |
| 1 | OT_IN (adapter OUT, PC817 open-collector, 10 kΩ pull-up) | interrupt-capable |
| 2 | OT_OUT (adapter IN, S8550 base drive) | high-Z; confirm idle polarity on devkit |
| 3 | RLY4 drive (DNP footprint) | 100 kΩ pull-down |
| 4 | BTN1 to GND, 10 kΩ pull-up, 100 nF | MTMS strap: SDIO only |
| 5 | BTN2 to GND, 10 kΩ pull-up, 100 nF | MTDI strap: SDIO only |
| 6 | I2C SDA (4.7 kΩ) | high-Z |
| 7 | I2C SCL (4.7 kΩ) | high-Z |
| 8 | STATUS LED, active-low, 3V3→R→LED→pin, 10 kΩ pull-up | **strap: must be high at reset** — LED + pull-up guarantee it |
| 9 | BOOT button + 2-pin jumper to GND, 10 kΩ pull-up | strap: low = download |
| 10 | ES1 — any-valve-open / end switch 1 | opto output, 47 kΩ pull-up, 1 µF |
| 11 | ES2 | as above |
| 12 | USB D− | reserved |
| 13 | USB D+ | reserved |
| 15 | OT activity LED, active-low, 10 kΩ pull-up | strap: JTAG select, ignored (eFuse 0) |
| 16 | spare header (U0TXD) | **ROM boot log at every reset; never a load** |
| 17 | spare header (U0RXD) | input w/ pull-up at boot |
| 18 | ES3 | opto output |
| 19 | DEMAND_IN (wired stat / cylinder stat, 24/230 V jumper) | opto output |
| 20 | MAINS_OK (wiring-centre L) | opto output |
| 21 | RLY1 (CH / zone 1) | 100 kΩ pull-down |
| 22 | RLY2 (HW / zone 2) | 100 kΩ pull-down |
| 23 | RLY3 (spare / zone 3) | 100 kΩ pull-down |
| EN | RESET button, 10 kΩ pull-up + 1 µF | — |

Pins used: 19 of 19. Expansion: I2C via Qwiic; GPIO16/17 on the spare header
are ordinary GPIO once booted.

## Firmware notes (decided by the hardware)

- Relay switches: `restore_mode: ALWAYS_OFF`; stagger pull-in 100 ms.
- `api: reboot_timeout: 0s` — default 15 min would reboot the board every 15
  minutes while HA is down.
- Heartbeat: if HA has not updated setpoints for N min, drop to fallback mode:
  DEMAND_IN → RLY1 + CH-enable, `t_set` from a simple outdoor curve, fixed
  `t_dhw_set`. Without HA and without DEMAND_IN wired, fallback is BOOST only.
- CH-enable gated on ES1 (`binary_sensor` with `delayed_on: 50ms`,
  `delayed_off: 100ms`). Stuck-output alarm as in §Boiler interlock.
- Weather compensation: HA computes flow setpoint, writes `t_set`. Boiler-side
  OTC only if the Viessmann has its own outdoor sensor.
- `sync_mode: true` if invalid-response errors appear with 1-Wire active.
- Verify on a C6 devkit + Melnyk adapter before layout: `opentherm` with WiFi
  and `one_wire` running.

## Power budget and surges

| Load | Peak | Typical |
|---|---|---|
| ESP32-C6 (WiFi TX, datasheet) | 382 mA | ~100 mA |
| 4 × relay coils (3 fitted) | 184 mA (138) | 92 mA |
| OLED + LEDs | 45 mA | 30 mA |
| LDO quiescent, 1-Wire, pull-ups | 10 mA | 5 mA |
| **Total at 5 V** | **~620 mA** | **~230 mA** |

Any 1 A USB-C brick leaves ~38 % headroom at worst case; a 500 mA laptop port
only matters during bench flashing with relays off.
The OT adapter's LED side is powered by the boiler's bus and the AC optos by
mains, so neither loads the 5 V rail.

Surges: mains side — the USB-C brick is the certified mains barrier and carries
its own protection; the board has no mains PSU. Relay coils — 1N4148W flyback on every coil. Relay contacts — 26 mA
motor load, nothing needed; load snubber position (100 nF X2 + 100 Ω brown–N)
left as optional DNP. USB — SMF5.0A TVS on VBUS, USBLC6-2SC6 on D±. Bulk 470 µF
on 5 V absorbs the relay pull-in step during a WiFi burst.

## Assembly plan

Everything surface-mount goes to JLCPCB. Through-hole is the easy stuff and
can be done by JLC (hand-solder fee ≈ $3.50/order + ~$0.017/joint) or at home:

| Part | Package | Who |
|---|---|---|
| ESP32-C6-WROOM-1 | castellated module, 1.27 mm pitch | JLC (in stock, 3.3k). Hand-solderable with a normal iron if ever needed |
| USB-C 16-pin | 0.5 mm pitch SMD | JLC — the one part that is genuinely fiddly by hand |
| Optos, MOSFETs, LDO, TVS, diodes, passives | SMD-4 / SOT-23 / SOT-223 / 1206 / 0603 | JLC |
| Relays, screw terminals, headers | THT | JLC THT assembly or home iron; all large pins |

No QFN, no BGA, no SC-70 on the board. Smallest hand-solder packages are
SOT-23 and 0603, and only the USB-C receptacle is below 1 mm pitch.

## Enclosure ★

IEC 60730-1 §21 / 60335-1 §30.2: parts supporting >0.2 A connections must pass
850 °C glow-wire, the rest 650 °C. PLA/PETG/plain ABS do not, and PLA creeps
above ~55 °C (airing cupboard 40–50 °C + 5–10 °C self-heating).

Owner's choice: print it, in a filament with a vendor UL94 V-0 claim. Plain ABS
is typically HB-rated, so look for "ABS-FR" / "V-0" on the spec (Polymaker
PC-FR, 3DXTech Firewire ABS/PC, Fillamentum ABS-FR, Kimya ABS-FR). ≥2.5 mm
walls, no vents above live parts, screwed lid. Fallback: off-the-shelf V-0 box
(Hammond 1591xxFL, Camdenboss CNMB) with a printed OLED bezel. Either way:
silk "230 V — ISOLATE AT FUSED SPUR BEFORE OPENING", wiring diagram in lid.

## Open questions

1. **Vitodens type code** (B1HA / B1HC / B1HF / B2HA / B2HF / WB1C…). 100-W
   and 050-W speak OpenTherm; 200-W / 222 / 242 do not. Also: with an OT
   master attached, does it still honour the 230 V demand input, and what does
   it do when OT comms stop? Decides whether Option A alone suffices.
2. Is anything wired to the boiler's OT terminals today?
3. S-plan (2 × 2-port) or Y-plan (mid-position valve)? Y-plan changes
   relay/sense wiring entirely.
4. Does the boiler have an outdoor sensor fitted (reports OT ID 27)?
5. Measured temperature at the mounting spot? (USB-C brick confirmed as supply.)
6. Mounting: metal screws to a backplate, or inside the existing wiring-centre box?
7. HW cylinder: stays on Viessmann's cylinder demand junction box, or moves
   under RLY2 + DEMAND_IN (cylinder stat)?

## BOM (JLCPCB, checked 2026-10-20)

| Ref | Part | LCSC | Lib | Stock | ~$ |
|---|---|---|---|---|---|
| U1 | ESP32-C6-WROOM-1-N8 | C5366877 | Ext | 3299 | 4.23 |
| U2 | AMS1117-3.3 | C6186 | **Basic** | 1M+ | 0.21 |
| U4–U10 | LTV-817S-TA1-C (2 × OT, 5 × AC sense) | C109227 | **Basic** | 208k | 0.08 |
| U11 | USBLC6-2SC6 | C7519 | Ext | 34k | 0.18 |
| K1–K4 | HF32FA-G/005-HSL1 (K4 DNP) | C91370 | Ext | 3432 | 1.61 |
| Q1–Q4 | AO3400A | C20917 | **Basic** | 1M+ | 0.10 |
| Q5 | S8550 PNP | C105432 | **Basic** | 192k | 0.02 |
| D* | 1N4148WS | C2128 | **Basic** | 2.7M | 0.02 |
| D* | SMF5.0A TVS | C193402 | Ext | 557k | 0.03 |
| ZD1–3 | BZT52C15 / C4V7 / C4V3 | C2104 / C2116 / C2115 | Ext | — | 0.02 |
| J1 | USB-C 16-pin HRO TYPE-C-31-M-12 | C165948 | Ext | 362k | 0.19 |
| J-mains | WJ128V-5.0-02P / 03P — **rising-cage clamp, ferrule-compatible (owner requirement)**; any substitute must be a 128-series cage type, never a 301-series screw-on-wire type | C8269 / C8270 | Ext | 72k / 31k | 0.15 / 0.21 |
| J-lv | KF350-3.5-2P / 3P | C474892 / C474893 | Ext | 12k / 3k | 0.12 / 0.16 |
| SW1–4 | TS-1187A-B-A-B tactile | C318884 | **Basic** | 292k | 0.02 |
| R-chain | 22 kΩ 1206 ×30 | basic | | | |
| C-bulk | 470 µF 105 °C (TBD at schematic) | | | | |

Rejected from review: MCP23008 expander (not needed on C6); NTC outdoor input
(DS18B20 probe only); MOV across relay contacts; HLK-PM01; AMS1117; LM66100
ideal diode (rev 3, hand-solder unfriendly, marginal benefit); on-board mains PSU
(IRM-05-5), fuse, MOV and UART header (rev 4: USB-C only, owner's decision);
LDL1117, PC817, LTV-814S, BC857B, 1N4148W (rev 5: Basic-library cost swaps).

## Toolchain

- KiCad 10.0.7; Konnect v0.13.0 (`~/.local/bin/konnect`, PCM plugin installed
  by hand under `~/Documents/KiCad/10.0/3rdparty/plugins/`); JLCPCB DB at
  `~/.konnect/jlcpcb.db`. KiCad API enabled. KiCad must be open with the board
  loaded only for PCB placement/routing.

## Schematic status (2026-10-20)

Drawn in `heating-controller.kicad_sch` (root) + `power_mcu`, `opentherm`,
`mains_io`. 158 components, every one with footprint and LCSC field. ERC on
the full hierarchy: **0 errors, 0 warnings**. Project libraries
`lib/jlc.kicad_sym` + `lib/jlc.pretty` + `lib/jlc.3dshapes` were generated
from JLC/EasyEDA data (easyeda2kicad) for the ESP32-C6-WROOM-1, HF32FA relay,
LTV-817S, TS-1187A, WJ128V and KF350 parts. Designators: sheet 2 = 1–99,
sheet 4 = 100-series, sheet 3 = 200-series. Style: net labels at every pin
(no wires) — electrically complete, dense. PDF: `docs/schematic.pdf`.

## Layout and routing (2026-10-20)

Board 150 × 95 mm, 2-layer, square outline, origin top-left. Mains along the
top edge (J110 mains in, J111–J114 relay outputs, relays K101–K104 at y 33),
AC sense chains and their optos to the right (x 97–133), the two sense
terminals J115/J116 on the right edge (x 143.5), SELV everything else below.
Isolation is enforced by geometry, not by hope:

- **Isolation band** rule area (no tracks, vias or pour on either layer):
  y 30–39 for x < 88 (between relay contact pins at y 25.4 and coil pins at
  y 40.6), stepping to y 48.5–55.5 for x > 93.5 (between opto LED pads at y 47
  and transistor pads at y 57). Only the relays and optos bridge it, as parts.
- **GND pours** (F + B) cover the SELV polygon only: (0,39)–(88.5,39)–(88.5,55.5)
  –(150,55.5)–(150,95)–(0,95). No pour anywhere in the 230 V region. Antenna
  keep-out (3–29, 87.2–95) under the ESP module end.
- **Slots** 1.0 mm wide (JLC minimum 0.65) on Edge.Cuts under the opto row
  (x 93–137, y 51.5–52.5) and between each relay's coil and contact pins
  (x ±8 around each relay, y 32.5–33.5). Silkscreen crossing a slot is clipped;
  that is the only remaining DRC warning class besides reference text over pads.
- Custom DRC (`heating-controller.kicad_dru`): MAINS+MAINS_SENSE ↔ everything
  else 6.4 mm; MAINS ↔ MAINS 1.4 mm; MAINS_SENSE ↔ MAINS 1.3 mm; MAINS tracks
  ≥ 2.0 mm; mains copper ≥ 2.0 mm from the edge.
- Net classes (in `.kicad_pro`): MAINS (L, N, COM1–4, NO1–4, DEMAND_RET)
  2.5 mm track / 2.0 mm clearance / 1.6 × 0.8 via; MAINS_SENSE (chain nodes,
  ES/DEMAND inputs, LEDA/LEDK) 0.5 / 0.5 / 1.0 × 0.5; Power (+5V, +3V3, GND)
  0.6 mm; Default 0.3 / 0.2 / 0.8 × 0.4. Board minimums: 0.15 mm track,
  0.3 mm copper-to-edge, 0.25 mm hole clearance.
- JLC assembly compliance: all courtyards inside the outline (J115/J116 moved
  in from x 146 to 143.5 for this), buttons ≥ 9 mm from the edge, 3 fiducials
  (FID1–3) in the SELV region, 4 × M3 holes at the corners ≥ 6.4 mm from mains
  copper, K104/D208 DNP.

### Routing pipeline (`tools/route/run_pipeline.sh <project_dir> [passes]`)

Freerouting 2.5 headless does the routing; the scripts only lay the few
things an autorouter cannot be trusted with and then restore the board. Close
the KiCad PCB editor before running: the board and project files are rewritten
on disk. Reproducible from the placed, unrouted board in about two minutes.

1. `prep_board.py` — writes the net classes and board minimums into
   `.kicad_pro`, insets the outline 0.15 mm (so the router's own edge clearance
   lands on the real edge), adds the isolation band, antenna keep-out, two
   temporary **bus corridors** (F.Cu y 10.5–21.5 and B.Cu y 10.5–26.5, x ≤ 138)
   and 2.2 mm **edge guards** around the 230 V region, then lays the fixed
   wiring as locked tracks: the L bus (F.Cu, y 12.5) and N bus (F.Cu, y 17)
   with their drops to the relay/sense terminals, the relay COM/NO links on
   B.Cu, the DEMAND_RET return (B.Cu y 28 → stub at x 126), the USB-C D+/D−
   pad bridges and the VBUS escape (vias at y 89.5, B.Cu link to D1), plus
   GND stitching vias on a 10 mm grid across the SELV region (31 on this
   revision; they keep the bottom pour in one piece where long B.Cu tracks run
   along the isolation band). Exports the Specctra DSN.
2. Freerouting: `-mp 40` passes; ends with "12 unrouted" internally, which are
   the locked nets and GND (left to the pours) — KiCad reports 0 unconnected.
3. `route_board.py` — restores the full outline and cuts the slots, imports
   the SES, strips every MAINS segment/via the round trip produced (text pass)
   and re-adds the buses deterministically, removes the corridors and guards,
   pours GND on both layers over the SELV polygon, fills, saves.
4. `kicad-cli pcb drc` (errors) → `fix_gaps.py` closes any sub-millimetre
   same-net gap the SES import leaves → DRC again. Result on this revision:
   **0 violations, 0 unconnected** (`fab/route/drc.json`, renders in
   `fab/route/board_top.png` / `board_bottom.png`).

Manual adjustments after routing should be limited to individual DRC fixes
or silkscreen tidying; anything structural goes into the scripts and is rerun.
