#!/bin/zsh
# Autoroute the board from the placed, unrouted layout.
# usage: tools/route/run_pipeline.sh <project_dir> [freerouting_passes]
# Close the KiCad PCB editor first: the scripts rewrite heating-controller.kicad_pcb and .kicad_pro on disk.
set -u -o pipefail
export PYTHONUNBUFFERED=1
P=$1; MP=${2:-40}
S=$(cd "$(dirname "$0")" && pwd)
PY=${KICAD_PY:-/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3}
CLI=${KICAD_CLI:-/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli}
JAVA=${JAVA:-/opt/homebrew/opt/openjdk/bin/java}
FRJAR=${FREEROUTING_JAR:-$HOME/.local/share/freerouting/freerouting-2.5.0.jar}
FILT='memory leak|assert|Debug:'
mkdir -p "$P/fab/route"
# the ESP32 module footprint has unnumbered thermal vias; give them a number and tie them to GND so the pours connect them
python3 -I - "$P/heating-controller.kicad_pcb" <<'PYEOF'
import re,sys
p=sys.argv[1]; s=open(p).read()
i=s.find('(property "Reference" "U1"'); a=s.rfind("\n\t(footprint",0,i); b=s.find("\n\t(footprint",i); b=len(s) if b<0 else b
blk=s[a:b]; n=blk.count('(pad "" thru_hole')
blk=re.sub(r'\(pad "" thru_hole circle\n(\t+)\(at ([^)]*)\)', lambda mm: '(pad "29" thru_hole circle\n'+mm.group(1)+'(at '+mm.group(2)+')\n'+mm.group(1)+'(net "GND")', blk)
s=s[:a]+blk+s[b:]; open(p,"w").write(s); print("ESP thermal vias tied to GND:", n)
PYEOF
echo "== prep"; (cd "$P" && "$PY" -I "$S/prep_board.py" "$P" 2>&1 | grep -v -E "$FILT"; st=${pipestatus[1]}; echo "prep status $st"; exit $st) || { echo "prep failed"; exit 1; }
echo "== freerouting"; (cd "$P/fab/route" && rm -f heating-controller.ses && "$JAVA" -jar "$FRJAR" -de heating-controller.dsn -do heating-controller.ses -mp "$MP" -l en 2>&1 | grep -E "stage completed|Optimization was completed|Saved" | tail -4)
echo "== import + pours"; (cd "$P" && "$PY" -I "$S/route_board.py" "$P" 2>&1 | grep -v -E "$FILT"; exit ${pipestatus[1]}) || { echo "route failed"; exit 1; }
cp "$P/fab/route/project.kicad_pro.bak" "$P/heating-controller.kicad_pro"; find "${P:?}" -maxdepth 1 -name "*.lck" -delete
echo "== drc"; "$CLI" pcb drc --severity-error --format json -o "$P/fab/route/drc.json" "$P/heating-controller.kicad_pcb" 2>&1 | tail -1
python3 -I "$S/fix_gaps.py" "$P/heating-controller.kicad_pcb" "$P/fab/route/drc.json"
echo "== silkscreen"; (cd "$P" && "$PY" -I "$S/silk.py" "$P" 2>&1 | grep -v -E "$FILT"); find "${P:?}" -maxdepth 1 -name "*.lck" -delete
"$CLI" pcb drc --severity-error --format json -o "$P/fab/route/drc.json" "$P/heating-controller.kicad_pcb" 2>&1 | tail -1
python3 -I -c "
import json; d=json.load(open('$P/fab/route/drc.json'))
from collections import Counter
v=d.get('violations',[]); u=d.get('unconnected_items',[])
print('DRC violations:',len(v),'unconnected:',len(u)); print(Counter(x['type'] for x in v).most_common(12))"
