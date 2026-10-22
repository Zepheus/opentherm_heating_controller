#!/bin/zsh
# JLCPCB manufacturing package: Gerbers + drill (zipped), placement file (CPL) and BOM, in fab/jlc/.
# Upload andiron-v1.0-gerbers.zip for the PCB, then andiron-bom-jlc.csv and andiron-cpl-jlc.csv for assembly.
# usage: tools/fab.sh [project_dir]
set -eu
P=${1:-$(cd "$(dirname "$0")/.." && pwd)}
CLI=${KICAD_CLI:-/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli}
B="$P/heating-controller.kicad_pcb"; O="$P/fab/jlc"; G="$O/gerbers"
rm -rf "$O"; mkdir -p "$G"
# Gerbers: JLC's KiCad recipe (Protel extensions, no X2, no netlist attributes, subtract mask from silk)
"$CLI" pcb export gerbers --no-x2 --no-netlist --subtract-soldermask --use-drill-file-origin \
  -l F.Cu,B.Cu,F.Paste,B.Paste,F.Silkscreen,B.Silkscreen,F.Mask,B.Mask,Edge.Cuts -o "$G/" "$B" | tail -1
# drill: Excellon, PTH and NPTH separate, mm, absolute origin as the Gerbers
"$CLI" pcb export drill --format excellon --excellon-separate-th --excellon-units mm --drill-origin plot \
  --excellon-zeros-format decimal --generate-map --map-format gerberx2 -o "$G/" "$B" | tail -1
(cd "$G" && zip -q -r "$O/andiron-v1.0-gerbers.zip" .)
# placement: every fitted part (SMD and through-hole), JLC column names and orientation corrections (tools/cpl.py)
KPY=${KPY:-/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3}
"$KPY" -I "$P/tools/cpl.py" "$B" "$P/docs/bom/andiron-bom-jlc.csv" "$O/andiron-cpl-jlc.csv"
cp "$P/docs/bom/andiron-bom-jlc.csv" "$O/"
ls -la "$O"; unzip -l "$O/andiron-v1.0-gerbers.zip" | tail -n +4 | awk '{print $4}'
