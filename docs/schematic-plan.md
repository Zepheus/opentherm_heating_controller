# Schematic structure

Hierarchical, four sheets, net labels at every pin (no wires).

## Sheets

| # | File | Contents |
|---|---|---|
| 1 | `heating-controller.kicad_sch` (root) | Title block and the three sheet blocks |
| 2 | `power_mcu.kicad_sch` | USB-C + protection, 5 V bulk, LDL1117 3.3 V regulator, ESP32-C6-WROOM-1 and decoupling, EN/RESET, BOOT button + jumper, BTN1/BTN2, STATUS/OT LEDs, OLED header and I2C pull-ups, Qwiic, 8-pin spare header, 1-Wire bus + FLOW/OUTDOOR terminals |
| 3 | `opentherm.kicad_sch` | Melnyk master adapter: fuse, bridge, TVS, zeners, 2 × LTV-817S, S8550, OT terminal |
| 4 | `relays.kicad_sch` | Four channels: HF115F changeover relay, AO3400A driver, gate resistors, flyback diode, coil LED, NC/COM/NO terminal |

## Nets

`+5V`, `+3V3`, `GND` are global and low-voltage only. Relay contact nets
`/Relays/NCn`, `/Relays/COMn`, `/Relays/NOn` (net classes CH1–CH4) stay within
their channel; nothing else may connect to them.

Signals crossing sheets (hierarchical labels):

| Net | GPIO | Direction (from MCU) | Sheet |
|---|---|---|---|
| OT_IN | 1 | in | OpenTherm |
| OT_OUT | 2 | out | OpenTherm |
| RLY1..RLY4 | 21, 22, 23, 3 | out | Relays |

Sheet-2-local: USB_DP/DN (12/13), SDA/SCL (6/7), ONEWIRE (0), BTN1/BTN2 (4/5),
LED_STATUS (8), LED_OT (15), BOOT (9), spare header IO10/IO11/IO18/IO19 and
SPARE16/SPARE17; IO20 not connected.

## Reference designators

Sheet 2: 1–99 (U1 module, U2 regulator, U3 USB ESD, J1 USB-C, J3 FLOW, J4
OUTDOOR, J5 OLED, J6 Qwiic, J7 spare, J8 BOOT jumper, SW1 RESET, SW2 BOOT, SW3
BTN1, SW4 BTN2, LED1 STATUS, LED2 OT). Sheet 3: 200-series (J201 OpenTherm,
F201 fuse, U201/U202 optos). Sheet 4: 100-series, one block per channel n
(K10n relay, Q10n driver, R1n1 gate, R1n2 pull-down, R1n3 LED resistor, D10n
flyback, LED10n, J11n terminal).
