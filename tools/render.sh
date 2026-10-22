#!/bin/zsh
# Render the board for the README: three ray-traced 3D views and two 2D layer plots.
# usage: tools/render.sh [project_dir]     (outputs to docs/images/)
set -eu
P=${1:-$(cd "$(dirname "$0")/.." && pwd)}
CLI=${KICAD_CLI:-/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli}
B="$P/heating-controller.kicad_pcb"; O="$P/docs/images"; mkdir -p "$O"
r() { "$CLI" pcb render --quality high --background opaque -w 2000 -h 1300 "$@" "$B" 2>&1 | tail -1; }
r --side top --perspective --rotate "-30,0,-18" --zoom 0.95 -o "$O/andiron-3d-iso.png"
r --side top    -o "$O/andiron-3d-top.png"
r --side bottom -o "$O/andiron-3d-bottom.png"
# 2D: copper, mask, silkscreen and outline per side, page fitted to the board
"$CLI" pcb export svg --mode-single --exclude-drawing-sheet --page-size-mode 2 --drill-shape-opt 2 \
  -l F.Cu,F.Mask,F.Silkscreen,Edge.Cuts -o "$O/andiron-2d-front.svg" "$B" 2>&1 | tail -1
"$CLI" pcb export svg --mode-single --exclude-drawing-sheet --page-size-mode 2 --drill-shape-opt 2 --mirror \
  -l B.Cu,B.Mask,B.Silkscreen,Edge.Cuts -o "$O/andiron-2d-back.svg" "$B" 2>&1 | tail -1
ls -la "$O"
