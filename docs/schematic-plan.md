# Schematic plan

Hierarchical, four sheets. Net names are fixed here so sheets can be drawn
independently and ERC'd together.

## Sheets

| # | File | Contents |
|---|---|---|
| 1 | `heating-controller.kicad_sch` (root) | Title, three sheet blocks, rail notes |
| 2 | `power_mcu.kicad_sch` | USB-C + protection, 5 V bulk, AMS1117-3.3, ESP32-C6-WROOM-1, decoupling, EN/RESET, BOOT button + jumper, BTN1/BTN2, STATUS/OT LEDs, OLED header + jumpers + I2C pull-ups, Qwiic, spare header, 1-Wire bus + FLOW/OUTDOOR terminals |
| 3 | `opentherm.kicad_sch` | Melnyk master adapter: bridge, zeners, 2 × LTV-817S, S8550, OT terminal |
| 4 | `mains_io.kicad_sch` | K1–K4 + AO3400A drivers + flyback + LEDs + COM/NO terminals + L/N terminals; 5 × AC sense channels (6 × 22 kΩ chain, 1N4148WS, LTV-817S, 47 kΩ, 1 µF) |

## Global nets (power symbols / global labels)

`+5V`, `+3V3`, `GND` — SELV only.
`MAINS_L`, `MAINS_N` — mains, never cross to SELV.

## Signals (hierarchical labels, sheet 2 ↔ 3/4)

| Net | GPIO | Dir (from MCU) | Sheet |
|---|---|---|---|
| OT_IN | 1 | in | 3 |
| OT_OUT | 2 | out | 3 |
| RLY1..RLY4 | 21,22,23,3 | out | 4 |
| ES1, ES2, ES3 | 10,11,18 | in | 4 |
| DEMAND_IN | 19 | in | 4 |
| MAINS_OK | 20 | in | 4 |

Sheet-2-local: USB_DP/DN (12/13), SDA/SCL (6/7), ONEWIRE (0), BTN1/BTN2 (4/5),
LED_STATUS (8), LED_OT (15), BOOT (9), SPARE16/17.

## Reference designator blocks

U1 ESP, U2 LDO, U3 USB ESD, U4–U5 OT optos, U6–U10 sense optos; K1–K4; Q1–Q4
relay FETs, Q5 OT PNP; J1 USB-C, J2 OT, J3 FLOW, J4 OUTDOOR, J5 OLED, J6 Qwiic,
J7 spare, J8 BOOT jumper, J10+ mains terminals; SW1 RESET, SW2 BOOT, SW3 BTN1,
SW4 BTN2; D1 VBUS TVS, D2.. flyback/bridge; ZD1–3; LED1 STATUS, LED2 OT,
LED3–6 relays.

## Order of work

1. Sheet 2 (power + MCU) → ERC clean on its own.
2. Sheet 3 (OT) → ERC.
3. Sheet 4 (mains I/O) → ERC.
4. Root: sheet pins imported, ERC on the whole hierarchy, netlist summary
   checked against the GPIO table, footprints assigned and verified against
   LCSC numbers, visual check of each sheet via PNG render.
