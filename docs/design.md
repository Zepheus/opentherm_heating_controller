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
2. A dead, held-in-reset, bootloading or brown-out board leaves every relay
   off (gate pull-downs, GPIOs high-impedance), so the zone valves spring
   closed and the boiler has no demand, **without firmware involvement**. A
   crashed firmware reaches the same state after the ESP-IDF task/interrupt
   watchdog resets the chip (5 s default in ESPHome); until then outputs hold.
   Loss of WiFi or Home Assistant does **not** release GPIOs: the firmware
   policy (R10.5) is to switch every relay and OT CH-enable off after 30 min
   without the HA heartbeat, and to never restore outputs at boot.
3. Residual modes that hardware does not clear: a GPIO held high by faulty
   firmware logic, a shorted driver MOSFET, welded contacts. That one zone
   stays on; the boiler keeps running under its own limit thermostat and
   flame supervision, as with a stuck relay in any wiring centre. Detected by
   the ES-live-while-commanded-off alarm (R10.5), never by a second relay.

(2) is achieved only by the wiring in §Boiler interlock. Do not deviate from it.

## Decisions (locked)

| Topic | Decision | Why |
|---|---|---|
| MCU ★ | ESP32-C6-WROOM-1-N8 (PCB antenna) | C3-MINI-1 has 13 usable GPIO; this design needs 18. C6 gives 19 usable after USB + UART, six real ADC inputs, same ESP-IDF/ESPHome path, native USB-Serial-JTAG. Zigbee radio unused but present |
| Firmware | ESPHome; OTGateway as OT-only fallback | ESPHome `opentherm` verified 2026-10-20 to expose everything needed (§Firmware). OTGateway has no zone/end-switch support so we do not design to its pin defaults |
| Programming | USB-C native USB-Serial-JTAG only; BOOT jumper + button; RESET button. No UART bridge, no UART header | Cable-only flashing and serial console; jumper for hands-free download mode. UART0 pins GPIO16/17 land on the spare header as plain GPIO |
| Power in | USB-C receptacle is the HRO TYPE-C-31-M-12 (C165948) to match KiCad's footprint. **USB-C 5 V only, from an external certified brick (≥1 A). A PD brick supplies 5 V by default via the CC resistors; no PD chip needed. No on-board mains PSU.** | Owner's decision. The brick is the certified mains barrier; the board's mains section is only the relay contacts and the sense inputs |
| 3.3 V | AMS1117-3.3, SOT-223 (Basic part) on ≥100 mm² pour | Rev 5 cost swap. 15 V abs-max Vin, 1 A; 1.7 V headroom from a 5.0 V brick against ~1.1 V dropout at 0.4 A; a sagging 4.5 V laptop port leaves 1.2 V, so the specified supply is a ≥ 1 A 5.0 V brick on a short cable and laptop ports are for flashing with relays off. Tab-connected 3V3 copper (~100 mm²) is a layout requirement, not optional. AP2112K rejected (6 V abs-max, SOT-23-5 thermals) |
| Relays | 4 × HF32FA-G/005-HSL1 footprints, 3 fitted. SPST-NO 10 A 250 VAC, 5 V coil 46 mA, "-G" reinforced (5 kV coil–contact), sealed | CH + HW + spare today; three zones + DHW/pump on a future combi. "-G" suffix confirmed in MPN. Sealed for lint |
| Relay drive | AO3400A low-side, 100 Ω gate series, 100 kΩ gate pull-down, 1N4148W flyback | Pull-down guarantees "off" whenever the GPIO is high-impedance: power-up, reset, bootloader, brownout, and a firmware crash (which ends in a watchdog reset). It does **not** cover a GPIO held high by faulty firmware logic, a shorted MOSFET or welded contacts: that zone then stays on, contained by the boiler's own limit stat (Type 1 control) and detected by the ES-live-while-off alarm (R10.5) |
| Relay LEDs ★ | 5 V → 1 kΩ → LED → MOSFET drain | Shows real coil state, costs no GPIO |
| Relay commons | Each relay has a 3-way terminal L / COM / NO (J111–J114). Installer links L–COM with a wire loop for switched-live, or leaves it open for volt-free | A solder jumper at 1.3 mm pitch cannot hold 230 V functional isolation when open, so the link lives in the terminal block |
| Contact protection | **None across contacts, no MOV anywhere.** No snubber footprints (26 mA motor load) | MOV across contacts fails short → valve permanently energised, defeats the interlock. V4043 motor is ~26 mA; 10 A AgSnO2 contacts need nothing |
| AC inputs | 5 × LTV-817S opto with anti-parallel 1N4148WS across the LED (half-wave; Basic parts): ES1–3 (valve end switches, J115, return = MAINS_N), DEMAND (J116: separate 230 V and 24 V input pins plus its own RET pin; the 24 V pin lands on the LED anode node and sees the three return-side resistors, 66 kΩ), MAINS_OK (senses board L, no terminal). Chain: 6 × 22 kΩ 1206 split 3 + 3 around the opto LED (input → 3 R → LED → 3 R → return; DEMAND: also 3 + 3, with the 24 V pin on the LED anode node) so both LED pins sit ≥ 66 kΩ from the 230 V terminals on every channel and the N return runs along the top corridor; ≈132 kΩ, 1.7 mA, 0.07 W and ~420 V impulse per part; 220 kΩ pull-up + 1 µF on the output. Outputs are active-low (`inverted: true`) | Impulse rating: 2.5 kV Cat II across 4 parts = 625 V each, above a generic 1206's ~400 V; six parts fixes it. Half-wave sensing gives 50 Hz pulses with ~10 ms gaps. Detector margin was checked with a time-domain model of the periodic steady state (constant CTR, 1.2 V LED, 0.1 V output floor), not peak-current arithmetic: with the original 47 kΩ/1 µF the output reached 0.89 V at 24 V and 1.40 V at 19.2 V, above the 0.825 V input-low limit; with 220 kΩ/1 µF and the 66 kΩ 24 V path it settles at 0.25 V at both 24 V and 19.2 V even at CTR 20 %, and the 230 V channels at 0.24 V down to 195 V. Release time (input removed to input-high) ≈ 42 ms. 230 V on the 24 V pin by mistake puts 0.8 W into the three return resistors, 0.27 W each against a 0.25 W rating at 70 °C: they run hot but within the part's overload envelope indefinitely, no failure is relied on; silkscreen says "230V OR 24V, NEVER BOTH" and "24V PIN IS LIVE IN 230V MODE". Surge: a 1.2/50 µs 2.5 kV impulse split six ways is ~420 V peak and ~0.3 mJ per part (7.9 W peak decaying with a 50 µs half-value). The exact part, Uniroyal 1206W4F2202T5E (C25830), is rated 200 V working, 400 V overload for 5 s and 500 V dielectric withstanding (datasheet §7, read 2026-10-20); Uniroyal publishes no pulse curve. The impulse is therefore 16 % under the withstanding voltage and five orders of magnitude under the 5 s overload energy (36 J). This is an engineering judgement from those ratings, not a surge test; if a tested figure is wanted the same footprint takes an anti-surge 1206 such as Yageo AC1206 without layout change |
| OpenTherm | Ihor Melnyk master adapter: 2 × LTV-817S, S8550 PNP, 1N4148WS bridge, zeners 4V7/15 V/4V3; F201 1 A 250 V fast SMD fuse (Bourns SF-2410FPA100W-2) in series with OT1, D208 SMAJ24A fitted across the bridge output; terminals 3.5 mm on the SELV edge, silk "OT 24V MAX" | Bus is boiler-powered SELV (~5–8 V / 15–18 V, 5–9 / 17–23 mA). Miswire coordination (R2.3): 230 V on OT1/OT2 drives the bridge into D208, which clamps at ≤ 39 V, so the fault current is limited only by F201, the diodes and the wiring: tens of amps, far above the fuse's 1 A rating. F201 (rated 250 VAC, 100 A breaking, I²t ≈ 0.6 A²s) clears in well under a millisecond; SMAJ24A survives 10 A for 1 ms (10/1000 µs rating) and far more for microseconds, and its failure mode under overload is a short, which still ends in F201 clearing. After clearing nothing conducts. The upstream BS1362 3 A fuse is the backstop if F201's breaking capacity were exceeded. This is a calculable fuse/TVS coordination rather than a hope that parts fail open; a bench fault test at 230 V through a current-limited source is on the test list. Normal signalling: ≤ 23 mA through ~0.1 Ω of fuse |
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

- Net classes MAINS (L, N, COM, NO, DEMAND_RET), MAINS_IN (the raw live terminal nets ES1_IN, ES2_IN, ES3_IN, DEMAND_230) and MAINS_SENSE (chain-internal nodes): 6.4 mm to every SELV net, vias and pours included. MAINS_IN additionally keeps 2.0 mm to every other net of any class; MAINS to MAINS 2.0 mm (62368-1 basic clearance at 2.5 kV is 1.5 mm); MAINS_SENSE to MAINS 1.3 mm, which only ever occurs across the body of a chain resistor carrying ~40 V.
- No copper pour on either layer in the mains region. Mains copper runs on both layers (N bus drops and relay COM/NO links cross under the L bus on the bottom); both faces are inside the enclosure and the same rules apply to both.
- 1.0 mm routed slot under every LTV-817S and between coil and contact pins of
  every relay, extending ≥3 mm past the body each end (opto pad-to-pad is only
  ~5.5 mm; relay coil–contact ~5–6 mm on the footprint).
- Mounting holes ≥6.4 mm from mains copper, or nylon standoffs.
- No silkscreen, test points or fiducials inside the isolation gap.
- All mains terminals on one board edge; USB-C, OT, 1-Wire, OLED, UART, Qwiic
  on the opposite edge. Cable-tie anchors on the mains side; OLED/sensor leads
  routed along the SELV edge.
- A strand escaping a mains screw terminal must not be able to reach SELV
  copper (60730-1 §11.2) — terminals face outward, SELV parts set back.
- The two OpenTherm optos sit SELV-to-SELV (OT bus is SELV from the boiler);
  their rating is not part of the mains barrier. The five AC-input LTV-817S
  are: Lite-On LTV-817S-TA1-C, 5000 Vrms, UL 1577 E113898, VDE DIN EN
  60747-5-5 cert. 40015248, EN 60950-1 (FIMKO/NEMKO/DEMKO/SEMKO); body 6.5 mm
  between pin rows, opposing pad edges 7.0 mm apart across the 1.0 mm slot.
  62368-1 reinforced at 230 V: 3.0/5.0 mm (OVC II), 5.5/5.0 mm (OVC III);
  the 6.4 mm floor meets both. Material group: standard FR-4 is CTI 175–250,
  group IIIa; the creepage figures above are taken for IIIb (CTI < 175),
  which is the conservative side. VDE 60747-5-5 working voltage: Lite-On's
  VDE table for the LTV-817 family gives VIORM 850 V peak (sources differ on
  whether the certificate number on the datasheet is the family's or a
  sibling's); 325 V peak is applied. Confirm against the certificate before a
  mains prototype is left unattended.
- Mains feed specification: one 230 V source, the 3 A (BS1362) fused spur
  that feeds the wiring centre. Every COM link and every sense input must be
  fed from that circuit and phase; a contact may be used volt-free only for a
  circuit fused at ≤ 3 A on the same phase, and never for a SELV circuit
  (the relay's contact-to-contact and contact-to-adjacent-terminal spacing is
  assessed for one mains circuit, not for mains-to-SELV separation). Loads
  are motorised valves (≤ 0.5 A); 10 A is the relay's rating, not the board's.
  Track withstand: 2.0 mm × 35 µm = 0.07 mm²; IEC 60364 adiabatic
  k = 115 (copper, 70 → 160 °C) gives (k·S)² ≈ 65 A²s, Onderdonk to 300 °C
  ≈ 190 A²s. A BS1362 3 A fuse's total clearing I²t is below 30 A²s at
  prospective currents of 1–6 kA (manufacturer curve to be filed with the
  wiring-centre documentation). Via barrels on the bus drops (0.8 mm drill,
  ~0.06 mm² of plating) feed only the sense chains (microamps), not the
  relay channels; the relay COM/NO links are 2.5 mm tracks without vias.
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
mains, so neither loads the 5 V rail. Supported power sources: a 5 V ≥ 1 A
USB-C brick on a short cable (normal operation); a laptop or hub port for
flashing with relays off (load < 0.4 A), accepting that the 470 µF bulk
capacitor's hot-plug inrush exceeds USB-IF guidance and may trip a port's
protection, in which case power from the brick and flash over WiFi. 1-Wire:
D2 (SMF5.0A, ~9 V clamp at 1 A) sits on the external node; R15 is 330 Ω
between that node and the MCU pin, so a clamped transient drives
(9 − 3.3 − 0.5)/330 ≈ 16 mA into the pin's internal diode for the pulse
duration, and a sensor pulling low still reads 0.6 V at the MCU (below the
0.825 V limit) through the 4.7 kΩ pull-up.

Surges: mains side — the USB-C brick is the certified mains barrier and carries
its own protection; the board has no mains PSU. Relay coils — 1N4148W flyback on every coil. Relay contacts — 26 mA
motor load, nothing needed; load snubber position (100 nF X2 + 100 Ω brown–N)
left as optional DNP. USB — SMF5.0A TVS on VBUS, USBLC6-2SC6 on D±. Bulk 470 µF
on 5 V absorbs the relay pull-in step during a WiFi burst; its hot-plug inrush
may trip a laptop hub's port protection, in which case power from the brick and
flash over WiFi. CC pull-downs (5.1 kΩ) only advertise a default sink: the full
620 mA peak needs the ≥ 1 A brick; a laptop port only ever sees the relays-off
load. OLED VCC option: the 5 V setting is for modules with their own regulator
and no 5 V I²C pull-ups; the ESP32-C6 is not 5 V tolerant, default is 3V3.

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
`mains_io`. 151 components, every one with footprint and LCSC field in the schematic (the PCB adds 4 mounting holes and 3 fiducials; PCB footprints do not carry the LCSC field, so the assembly BOM is exported from the schematic and the CPL from the board). ERC on
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
  copper, K104 DNP (D208 fitted since the review). F201 (OT fuse) at (64, 82)
  between the regulator and the sensor terminals.

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
   pad bridges and the VBUS escape (vias at y 89.5, B.Cu link to D1), the
   +3V3 bars around the regulator tab, the four raw live inputs in full (at
   2.0 mm clearance the autorouter cannot thread them through the sense
   columns: each leaves its resistor pad upward, drops to B.Cu, runs down
   beside its column to its own lane and east to its terminal; the lanes
   cannot cross each other's drops, so J115 is wired ES3/ES2/ES1 from the top
   and DEMAND_230 takes the highest lane and rises to J116 pin 1 on F.Cu at
   x 139.8; DEMAND_24 is pre-routed round the east side of the terminals for
   the same reason), plus GND stitching vias on a
   10 mm grid across the SELV region (30 on this revision; they keep the
   bottom pour in one piece where long B.Cu tracks run along the isolation
   band). Exports the Specctra DSN.
2. Freerouting: `-mp 40` passes; ends with "12 unrouted" internally, which are
   the locked nets and GND (left to the pours) — KiCad reports 0 unconnected.
3. `route_board.py` — restores the full outline and cuts the slots, imports
   the SES, strips every MAINS segment/via the round trip produced (text pass)
   and re-adds the buses deterministically, removes the corridors and guards,
   pours GND on both layers over the SELV polygon, fills, saves.
4. `kicad-cli pcb drc` (errors) → `fix_gaps.py` closes any sub-millimetre
   same-net gap the SES import leaves → `silk.py` lays the board-level
   silkscreen → DRC again. Result on this revision: **0 violations,
   0 unconnected** (`fab/route/drc.json`, renders in `fab/route/board_top.png`
   / `board_bottom.png`).

Manual adjustments after routing should be limited to individual DRC fixes
or silkscreen tidying; anything structural goes into the scripts and is rerun.

## Independent review, 2026-10-20: what changed

Two rounds of an independent design-file review (the review document itself
was removed once closed; `layout-notes.md` keeps the lessons). Changes made:

1. OpenTherm: U201 pin 3 and D207 cathode moved from OT_N1 to their own net
   OT_TXE (a net merge against the Melnyk reference that would have echoed
   our own transmissions into the RX opto). D208 fitted. F201, a 1 A 250 V
   fast 2410 fuse, added in series with OT1 (see the OpenTherm row).
2. Net class MAINS_IN for the four raw live inputs, 2.0 mm to everything;
   mains-to-mains 1.4 → 2.0 mm; the 6.4 mm and edge rules include the class.
3. Demand chain changed from 4 + 2 to 3 + 3 and all five opto pull-ups from
   47 kΩ to 220 kΩ after a time-domain model showed the 24 V detector had no
   margin (AC-inputs row).
4. +3V3 copper on the regulator tab (locked bars plus pour, ~135 mm²).
5. 1-Wire series resistor R15 100 Ω → 330 Ω to limit clamp current into the
   MCU pin during a surge.
6. Silkscreen labels at every terminal pin, warnings at J116 and J201,
   revision string; LCSC/Description/Datasheet fields copied into the PCB
   footprints so schematic parity is clean.
7. Documentation corrected where it had drifted from the files (layer
   policy, track width, resistor split, headroom, part names, counts,
   fail-safe wording, material group).

Still to do before fabrication: library refresh to clear the benign
symbol/footprint mismatch warnings (ESP thermal pad numbering and relay pin
types are intentional), BOM from schematic and CPL from board, plotted
silkscreen inspection, assembler DFM. Bench before any mains connection: 3V3
rail start-up and load step, 24 V demand margin, OT TX/RX against a
simulator, F201/D208 fault test through a current-limited source.
