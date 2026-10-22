# tools

Everything needed to regenerate the board outputs from the KiCad sources.
The KiCad Python scripts must run under KiCad's own interpreter, in isolated
mode (`-I`), with the PCB editor closed:

```sh
KPY=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3
```

| Script | Run with | What it does |
|---|---|---|
| `layout/geometry.py` | — | Shared board geometry: relay row, terminal positions, contact columns, channel zones, isolation band, slots, antenna keep-out. Read by placement, pre-routing, routing and silkscreen. |
| `layout/place.py <board>` | `$KPY -I` | Places every part by module area; writes the board outline. |
| `sync_netlist.py <project> <board>` | `$KPY -I` | Headless "Update PCB from schematic": adds/removes footprints, swaps changed footprints, copies values and fields, assigns pad nets. |
| `route/run_pipeline.sh <project> [passes]` | zsh | Full layout regeneration: 3D model sync, prep (net classes, rule areas, locked pre-routes, stitching), Freerouting, SES import, pours and island repair, silkscreen, DRC. 40 passes, about a minute. |
| `route/prep_board.py` | `$KPY -I` | Stage 1 of the pipeline. All hand-routed copper (mains buses, relay links, live-input lanes, USB, regulator copper) lives here. |
| `route/route_board.py` | `$KPY -I` | Stage 2: SES import, re-lays mains copper, slots, GND and 3V3 pours, island repair. |
| `route/placed.kicad_pcb` | — | The placed, unrouted board the pipeline starts from. Make placement changes here (open it in KiCad), then rerun the pipeline. |
| `route/fix_gaps.py` | `python3` | Closes sub-millimetre same-net gaps left by the SES round trip. |
| `route/clean_dangling.py` | `$KPY -I` | Removes vias and stubs that DRC reports as dangling, one pass per run, reverting any pass that would disconnect something. |
| `route/silk.py` | `$KPY -I` | Board-level silkscreen, positioned from the footprints: channel and pin labels, connector names, warnings, identity. Idempotent. |
| `sync_models.py <project>` | `$KPY -I` | Relinks every footprint to its 3D model with portable paths. |
| `bom.py [project] [--boards N]` | `python3` | BOM with cost estimates from the schematic and the Konnect JLCPCB database. |
| `render.sh [project]` | zsh | 3D renders and 2D layer plots for the README. |
| `check/sanity.py <board>` | `$KPY -I` | Pre-fabrication report: spacing rules from `check/spacing_rules.json` encoded in the DRC file, rule areas and slots present, track widths per class, JLCPCB drill and annular limits, decoupling distances, antenna keep-out, tallest parts. Exit 1 on failure; the pipeline runs it last. |
| `check/spacing_rules.json` | — | The isolation and spacing requirements, each with its basis. |
| `check/pour_islands.py <board>` | `$KPY -I` | Lists GND pour islands and what they contain; DRC does not report silently removed copper. |
| `konnect/kon.py` | `python3` | Calls Konnect MCP tools from a script, without an MCP client. |
| `konnect/labeler.py` | `python3` | Places schematic net labels at pin endpoints from a JSON net map (schematic capture style used here). |
| `oneoff/` | — | Dated one-off migrations kept for the record; not meant to be rerun. |

Environment overrides: `KICAD_CLI`, `KICAD_PY`, `JAVA`, `FREEROUTING_JAR`,
`KONNECT`, `JLC_DB`, `JLC_EXTENDED_FEE`.

Design requirements and rules that these scripts implement live in
`docs/requirements.md`, `heating-controller.kicad_dru` and
`.konnect/project.json`; lessons learned in `docs/layout-notes.md`.
