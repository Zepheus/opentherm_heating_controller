# Andiron — working rules

ESP32-C6 heating controller PCB (KiCad 10, JLCPCB assembly), designed for an
ESPHome firmware controlled from Home Assistant. Read `docs/requirements.md`
(what), `docs/design.md` (why) and `docs/layout-notes.md` (layout lessons)
before changing anything.

## BOM and cost — always current

- After **any** schematic change (part added, removed, value, footprint, LCSC
  number or DNP state), run `python3 tools/bom.py` and commit the regenerated
  `docs/BOM.md` and `docs/bom/andiron-bom-jlc.csv` in the same commit.
- Every fitted part must have an LCSC number that resolves in the JLCPCB
  database; `tools/bom.py` lists any that do not, and that list must be empty.
- The BOM always carries a cost estimate: per-board component cost, the
  Extended-part loading fees, and the per-board total for the planned run.
  When a change moves the per-board total, say so (old → new) in the commit
  message and to the user.
- Prefer JLCPCB Basic parts. Before adding an Extended part, check for a Basic
  equivalent and note in `docs/design.md` why the Extended one was chosen.
- Update the cost line in `README.md` if the rounded figures change.

## Schematic and board

- Every component carries an LCSC field; Description and Datasheet fields are
  copied into the PCB so `kicad-cli pcb drc --schematic-parity` stays clean
  (only the 7 board-only holes and fiducials may remain).
- The board is routed by `tools/route/run_pipeline.sh`, not by hand. Change
  placement or pre-routes in the scripts and rerun; close the KiCad PCB editor
  first because the pipeline rewrites the files on disk.
- Done means: ERC 0 errors, DRC 0 errors and 0 unconnected, parity clean,
  all courtyards inside the outline, pour areas checked
  (`tools/check/pour_islands.py`). Then regenerate the BOM and the renders
  (`tools/render.sh`).
- Mains rules are not negotiable: 6.4 mm mains-to-SELV, the net classes and
  slots in `heating-controller.kicad_dru` and `.konnect/project.json`. Any
  change to them is a design decision recorded in `docs/design.md`.
- Keep reusable scripts in `tools/` (see `tools/README.md`), never only in a
  scratch directory. Record routing or margin lessons in
  `docs/layout-notes.md`.

## Writing

- Do not name commercial products this board might replace or compete with.
- Document design decisions in `docs/design.md`, not in commit messages only.
