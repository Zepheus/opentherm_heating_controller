"""Remove the vias and track stubs that KiCad's own DRC reports as dangling (Freerouting leftovers), then verify.

Reads fab/route/drc.json, deletes each via flagged via_dangling and each segment flagged track_dangling, reruns DRC and
does one pass per process (KiCad's Python cannot load a board twice in one process; the runner calls it up to
three times). If the pass increases the unconnected count, the board is restored from before that
pass and the script stops, so it can never break connectivity.
usage: <kicad python> -I tools/route/clean_dangling.py <project_dir>
"""
import sys, json, shutil, subprocess, os, pcbnew
P = sys.argv[1]; B = P + "/heating-controller.kicad_pcb"; J = P + "/fab/route/drc.json"
CLI = os.environ.get("KICAD_CLI", "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli")
def drc():
    subprocess.run([CLI, "pcb", "drc", "--severity-all", "--format", "json", "-o", J, B], capture_output=True)
    d = json.load(open(J)); return d, len(d["unconnected_items"])
d, unc0 = drc(); removed = 0
for _ in range(1):
    targets = [(v["type"], i["pos"]["x"], i["pos"]["y"]) for v in d["violations"] if v["type"] in ("via_dangling", "track_dangling") for i in v["items"]]
    if not targets: break
    shutil.copy(B, B + ".bak")
    board = pcbnew.LoadBoard(B); n = 0
    for t in list(board.GetTracks()):
        if t.IsLocked() or t.GetNetname() == "GND": continue
        for kind, x, y in targets:
            if kind == "via_dangling" and t.GetClass() == "PCB_VIA" and abs(t.GetPosition().x / 1e6 - x) < 1e-3 and abs(t.GetPosition().y / 1e6 - y) < 1e-3:
                board.Remove(t); n += 1; break
            if kind == "track_dangling" and t.GetClass() == "PCB_TRACK" and any(abs(pt.x / 1e6 - x) < 1e-3 and abs(pt.y / 1e6 - y) < 1e-3 for pt in (t.GetStart(), t.GetEnd())):
                board.Remove(t); n += 1; break
    pcbnew.ZONE_FILLER(board).Fill(board.Zones()); pcbnew.SaveBoard(B, board)
    d, unc = drc()
    if unc > unc0:
        lost = unc - unc0; shutil.copy(B + ".bak", B); d, unc = drc(); print(f"remaining items are load-bearing ({lost} would disconnect); pass reverted"); break
    removed += n
if os.path.exists(B + ".bak"): os.remove(B + ".bak")
left = sum(1 for v in d["violations"] if v["type"] in ("via_dangling", "track_dangling"))
print(f"dangling items removed: {removed}; still dangling: {left}; unconnected: {len(d['unconnected_items'])}")
