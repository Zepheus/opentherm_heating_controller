# Requirements — Andiron heating controller

Numbered so the schematic, layout and firmware can be checked against them.
Design rationale and part choices live in `design.md`; this file is *what*,
not *why*.

## R1 Purpose and system role
- R1.1 Control a UK domestic heating system from its wiring centre: zone valves,
  boiler demand and an OpenTherm boiler link.
- R1.2 The board is an I/O device controlled by Home Assistant over WiFi; it
  holds no schedule of its own. Firmware is ESPHome.
- R1.3 Radiator valves and room sensors are out of scope; Home Assistant
  integrates them separately.
- R1.4 Must serve the current system boiler + hot-water cylinder, and a future
  combi boiler with up to three heating zones, with no board change.

## R2 Boiler interface — OpenTherm master
- R2.1 One OpenTherm master port, polarity independent, galvanically isolated
  from the ESP, on 3.5 mm cage-clamp terminals on the low-voltage edge.
- R2.2 Must support the ESPHome `opentherm` component: CH enable, CH setpoint,
  DHW enable, DHW setpoint, modulation, flow/return/outdoor temps, fault bits.
- R2.3 Miswiring 230 V to the OT terminals must not start a fire: a series
  250 V-rated fuse and a TVS across the bridge output form a calculable
  crowbar (the TVS clamps, the fuse clears in under a millisecond); the
  adapter may be damaged, nothing is relied on to fail open; silk
  "OT 24V MAX".
- R2.4 Target boiler: Viessmann Vitodens (model code TBC; must be a 100-W/050-W
  class that speaks OpenTherm).

## R3 Zone valve outputs
- R3.1 Four relay channels on the PCB, three fitted: SPST-NO, ≥10 A 250 VAC,
  reinforced coil–contact insulation, sealed. 5 V coils from the USB rail.
- R3.2 Each channel: separate COM terminal with a solder-link to board L, so a
  channel can be switched-live or volt-free.
- R3.3 Every output is OFF through power-up, reset, bootloader, brownout and
  firmware crash (watchdog reset), by hardware (gate pull-downs), not firmware.
  A firmware-logic fault, shorted driver or welded contact is not covered by
  hardware: it leaves one zone on, contained by the boiler's own limits and
  detected per R10.5.
- R3.4 A relay's indicator LED shows the real coil state (wired to the drive
  node, not a GPIO).
- R3.5 No MOV or snubber across contacts. Optional DNP load snubber per channel.
- R3.6 All mains terminals: rising-cage clamp screw blocks accepting ferruled
  1.0–1.5 mm² flex, 5 mm pitch, ≥250 V / ≥10 A.

## R4 230 V sense inputs
- R4.1 Five opto-isolated 230 V AC inputs, each reading "live present":
  ES1–ES3 (valve end switches), DEMAND_IN (wired room stat or cylinder stat;
  solder-jumper for 24 V AC stats), MAINS_OK (wiring-centre L).
- R4.2 Series resistor chain rated for a 2.5 kV OVC II impulse and <0.1 W per
  resistor; output filtered to a steady level at 50 Hz.
- R4.3 ES1 is the "any valve open" interlock input (see R10.2).

## R5 Power and programming
- R5.1 USB-C is the only power input and the only programming path. 5 V from an
  external certified brick, ≥1 A. CC pull-downs so PD and C-to-C cables work.
- R5.2 No on-board mains PSU, no UART-to-USB bridge, no UART header.
- R5.3 USB port protected: VBUS TVS, D± ESD array, shield to GND via R‖C.
- R5.4 ≥470 µF bulk on 5 V; LDO rated ≥1 A with ≥15 V abs-max input.
- R5.5 Worst-case board draw ≤ 650 mA at 5 V.
- R5.6 BOOT button, 2-pin BOOT jumper and RESET button on the SELV edge.

## R6 MCU
- R6.1 ESP32-C6-WROOM-1-N8 (PCB antenna), antenna over the board edge in the
  Espressif keep-out, on the SELV edge away from relays.
- R6.2 GPIO assignment as in `design.md` §GPIO map. Relay drives only on
  non-strapping pins; strapping pins carry only pulled-up buttons/LEDs.

## R7 User interface
- R7.1 4-pin I2C OLED header (SSD1306/SH1106, 0x3C), pin-1/2 swap solder
  jumpers, VCC 3V3/5V select, on-board 4.7 kΩ pull-ups (DNP-able).
- R7.2 Two general-purpose buttons BTN1/BTN2 (function set in firmware).
- R7.3 Status LED and OT-activity LED on the SELV edge.

## R8 Sensors
- R8.1 One 1-Wire bus with two 3-pin terminals (3V3, DATA, GND): FLOW and
  OUTDOOR, for waterproof DS18B20 probes. 4.7 kΩ pull-up, series R, TVS.

## R9 Expansion
- R9.1 Qwiic/STEMMA-QT JST-SH 4-pin on the I2C bus.
- R9.2 4-pin spare header: GPIO16, GPIO17, 3V3, GND.

## R10 Safety
- R10.1 Isolation mains↔SELV: design floor 6.4 mm clearance and creepage
  (reinforced per IEC 62368-1 is 3.0/5.0 mm). Slots under optos and between
  relay coil/contact pins. No pour in the mains region on either layer; mains copper may use both layers.
- R10.2 Boiler interlock is in the wiring, not the firmware: valve end switches
  feed the boiler's 230 V demand input as in a standard S-plan; the board only
  senses that node (ES1) and gates OT CH-enable on it. The boiler's switched
  live is never linked out.
- R10.3 Mains buses 2.5 mm, no mains track under 2.0 mm; all mains terminals on one edge; cable anchors;
  a loose strand from a mains terminal cannot reach SELV copper.
- R10.4 Enclosure: printed in a UL94 V-0 rated filament (ABS-FR/PC-FR), ≥2.5 mm
  walls, screwed lid, no vents above live parts, warning label. A filament's
  V-0 rating is for the raw material; the printed wall is not certified.
- R10.5 Firmware: `restore_mode: ALWAYS_OFF`; `api.reboot_timeout: 0s`; HA
  heartbeat: after 30 min without it every relay and OT CH-enable go off;
  task/interrupt watchdogs left at their ESP-IDF defaults (reset on hang);
  stuck-output alarm (ES live while relay off). A firmware fault that holds a
  relay on is not detectable by the alarm and is accepted as residual.

## R11 Manufacturing and cost
- R11.1 JLCPCB economic assembly, 2-layer. All SMD placed by JLC; THT by JLC.
- R11.2 Prefer Basic-library parts; every part has a verified LCSC number.
- R11.3 No package below SOT-23/0603 except the USB-C receptacle. No QFN/BGA.
- R11.4 Target ≈ $32 per board at a run of 5, before VAT.

## R12 Open items (do not block the schematic)
- Viessmann model code; whether it honours the 230 V demand input with an OT
  master attached; outdoor sensor fitted?
- S-plan vs Y-plan.
- Mounting location and measured temperature.
- Whether HW stays on Viessmann's cylinder-demand box.
