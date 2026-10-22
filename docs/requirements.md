# Requirements — Andiron heating controller

Numbered so the schematic, layout and firmware can be checked against them.
Design rationale and part choices live in `design.md`; this file is *what*,
not *why*.

## R1 Purpose and system role
- R1.1 Control a UK domestic heating system from its wiring centre: switch the
  zone valves and the boiler demand, and talk to an OpenTherm boiler.
- R1.2 The board is an I/O device controlled by Home Assistant over WiFi; it
  holds no schedule of its own. Firmware is ESPHome.
- R1.3 Radiator valves and room sensors are out of scope; Home Assistant
  integrates them separately.
- R1.4 Must serve the current system boiler + hot-water cylinder (S-plan or
  Y-plan), and a future combi boiler with up to three heating zones, with no
  board change.

## R2 Boiler interface — OpenTherm master
- R2.1 One OpenTherm master port, polarity independent, galvanically isolated
  from the ESP, on 3.5 mm cage-clamp terminals on the low-voltage edge.
- R2.2 Must support the ESPHome `opentherm` component: CH enable, CH setpoint,
  DHW enable, DHW setpoint, modulation, flow/return/outdoor temps, fault bits.
- R2.3 Miswiring 230 V to the OT terminals must not start a fire: a series
  250 V-rated fuse and a TVS across the bridge output form a calculable
  crowbar; the adapter may be damaged, nothing is relied on to fail open.
- R2.4 Target boiler: Viessmann Vitodens (model code TBC; must be a 100-W/050-W
  class that speaks OpenTherm).

## R3 Relay outputs
- R3.1 Four relay channels, all fitted, CH1–CH4. Each is a **volt-free
  changeover contact** (COM, NO, NC) on its own 3-way terminal, like the
  outputs of common UK heating controllers: NO switches a valve or a boiler
  demand loop, NC provides the "hot water off" signal a Y-plan mid-position
  valve needs.
- R3.2 Contacts ≥250 VAC; the board is rated 3 A per channel (wiring-centre
  spur fuse). Relays with reinforced coil-to-contact insulation (≥4 kV),
  sealed, 5 V coils from the USB rail.
- R3.3 No mains supply input and no mains link on the board: when a channel
  must switch live, the wiring centre feeds its own fused live into COM.
- R3.4 Each channel is isolated from every other channel and from all
  low-voltage circuits (reinforced), so one channel may switch 230 V while
  another closes a boiler's low-voltage demand loop.
- R3.5 Every output is OFF through power-up, reset, bootloader, brownout and
  firmware crash (watchdog reset), by hardware (gate pull-downs), not firmware.
  A firmware-logic fault, shorted driver or welded contact is not covered by
  hardware and is accepted as residual (see design.md §Safety framing).
- R3.6 A relay's indicator LED shows the real coil state (wired to the drive
  node, not a GPIO).
- R3.7 No MOV or snubber across contacts.
- R3.8 Relay terminals: rising-cage clamp screw blocks accepting ferruled
  1.0–1.5 mm² flex, 5 mm pitch, ≥250 V / ≥10 A.

## R4 Power and programming
- R4.1 USB-C is the only power input and the only programming path: 5 V from
  an external certified brick, ≥1 A. CC pull-downs so C-to-C cables work.
- R4.2 No on-board mains power supply, no UART-to-USB bridge, no UART header.
- R4.3 USB port protected: VBUS TVS, D± ESD array, shield to GND via R‖C.
- R4.4 Relay coils run from 5 V directly; 3.3 V from a linear regulator that
  needs ≤0.5 V headroom at 400 mA, is stable with ceramic capacitors and
  tolerates ≥15 V on its input. No exposed-pad or heatsink-copper parts.
- R4.5 ≥470 µF bulk on 5 V. Worst-case board draw ≤ 800 mA at 5 V.
- R4.6 BOOT button, 2-pin BOOT jumper and RESET button.

## R5 MCU
- R5.1 ESP32-C6-WROOM-1-N8 (PCB antenna). The antenna end sits at the board
  edge with no copper under it and no metal (terminals, USB shell, screws)
  near it.
- R5.2 GPIO assignment as in `design.md` §GPIO map. Relay drives only on
  non-strapping pins; strapping pins carry only pulled-up buttons/LEDs.

## R6 User interface
- R6.1 4-pin I2C OLED header, GND / 3V3 / SCL / SDA (standard SSD1306/SH1106
  modules, 0x3C), on-board 4.7 kΩ pull-ups.
- R6.2 Two general-purpose buttons BTN1/BTN2 (function set in firmware).
- R6.3 Status LED and OT-activity LED.

## R7 Sensors and expansion
- R7.1 One 1-Wire bus with two 3-pin terminals (3V3, DATA, GND): FLOW and
  OUTDOOR, for waterproof DS18B20 probes. 4.7 kΩ pull-up, series R, TVS.
- R7.2 Qwiic/STEMMA-QT JST-SH 4-pin on the I2C bus.
- R7.3 8-pin spare header: GPIO16, GPIO17, GPIO10, GPIO11, GPIO18, GPIO19,
  3V3, GND.

## R8 Safety
- R8.1 Isolation between each relay channel and anything else: design floor
  6.4 mm clearance and creepage (reinforced per IEC 62368-1 is 3.0/5.0 mm),
  with routed slots between each relay's coil and contacts and between
  channels. Contacts of one channel: 2.0 mm. No copper pour near contacts.
- R8.2 Contact copper ≥2.0 mm wide (links 2.5 mm), ≥2.0 mm from the board
  edge; relay terminals on one edge, a loose strand cannot reach
  low-voltage copper.
- R8.3 Spacing limits are a checked specification, not prose:
  `tools/check/spacing_rules.json` lists every limit with its basis;
  `heating-controller.kicad_dru` encodes them so DRC enforces them on every
  run; `tools/check/sanity.py` fails if a rule, the isolation band, the
  antenna keep-out or the isolation slots go missing.
- R8.4 The boiler's own controls (limit stat, flame supervision) stay the
  safety layer; the boiler interlock lives in the wiring centre's wiring.
- R8.5 Enclosure: printed in a UL94 V-0 rated filament (ABS-FR/PC-FR), ≥2.5 mm
  walls, screwed lid, no vents above live parts, warning label. A filament's
  V-0 rating is for the raw material; the printed wall is not certified.
- R8.6 Firmware: `restore_mode: ALWAYS_OFF`; `api.reboot_timeout: 0s`; after
  30 min without the Home Assistant heartbeat every relay and OT CH-enable go
  off; task/interrupt watchdogs left at their ESP-IDF defaults (reset on hang).

## R9 Manufacturing and cost
- R9.1 JLCPCB economic assembly, 2-layer. All SMD placed by JLC; THT by JLC.
- R9.2 Prefer Basic-library parts; every part has a verified LCSC number.
- R9.3 No package below SOT-23/0603 except the USB-C receptacle. No QFN/BGA.
- R9.4 Bill of materials with cost estimate kept in `docs/BOM.md`.

## R10 Open items (do not block the board)
- Viessmann model code and its behaviour when OT communication stops; outdoor
  sensor fitted?
- S-plan vs Y-plan at the current install.
- Mounting location and measured temperature.
