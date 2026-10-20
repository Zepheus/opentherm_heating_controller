# Heating controller

ESP32-C6 / ESPHome heating controller replacing a Drayton Wiser Heat Hub R:
OpenTherm master, 4 × 230 V zone-valve relays (3 fitted), 5 × opto-isolated
230 V sense inputs, USB-C power + programming, OLED, two buttons, 1-Wire
probes. Target: JLCPCB economic assembly.

- `docs/requirements.md` — numbered requirements (what)
- `docs/design.md` — decisions, safety framing, GPIO map, BOM, open questions (why)
- `docs/schematic-plan.md` — sheet structure and net names
- `heating-controller.kicad_pro` — KiCad 10 project; `lib/` holds project symbols/footprints/3D
- `.konnect/project.json` — design rules enforced by Konnect during layout

Open questions that must be answered before the board is ordered are at the
end of `docs/design.md` (boiler model code is the big one).
