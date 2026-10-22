"""Relink every board footprint to its library 3D model(s), with portable paths.

Footprints placed through Konnect lost their (model ...) entries, and easyeda2kicad wrote absolute paths into the
project library. This copies the models from the library footprint into each board footprint, rewrites project-library
paths to ${KIPRJMOD}/lib/jlc.3dshapes/..., and fixes the same paths in lib/jlc.pretty itself. Idempotent.

The HRO USB-C receptacle has no model in KiCad 10 either; the GCT USB4105 model stands in.
The ESP32-C6-WROOM-1 has no model in either library; KiCad's ESP32-S3-WROOM-1 model has the same 18 x 25.5 mm body
and pad columns and is used as a visual stand-in, shifted so its pin 1 lands on ours.

usage: <kicad python> -I tools/sync_models.py <project_dir>
"""
import sys, os, re, glob, pcbnew

P = sys.argv[1]
B = P + "/heating-controller.kicad_pcb"
KICAD_FP = "/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints"
JLC_3D = "${KIPRJMOD}/lib/jlc.3dshapes/"

# 1. portable paths inside the project library
for f in glob.glob(P + "/lib/jlc.pretty/*.kicad_mod"):
    s = open(f).read()
    t = re.sub(r'\(model "[^"]*/jlc\.3dshapes/([^"]+)"', lambda m: '(model "%s%s"' % (JLC_3D, m.group(1)), s)
    if t != s: open(f, "w").write(t)

def lib_path(nick):
    return P + "/lib/jlc.pretty" if nick == "jlc" else "%s/%s.pretty" % (KICAD_FP, nick)

board = pcbnew.LoadBoard(B)
cache, linked, missing = {}, 0, []
for fp in list(board.Footprints()):
    fpid = fp.GetFPID(); nick, name = str(fpid.GetLibNickname()), str(fpid.GetLibItemName())
    if (nick, name) not in cache:
        cache[(nick, name)] = pcbnew.FootprintLoad(lib_path(nick), name) if os.path.isdir(lib_path(nick)) else None
    lib = cache[(nick, name)]
    models = list(lib.Models()) if lib is not None else []
    if name == "WIRELM-SMD_ESP32-C6-WROOM-1":
        m = pcbnew.FP_3DMODEL()
        m.m_Filename = "${KICAD10_3DMODEL_DIR}/RF_Module.3dshapes/ESP32-S3-WROOM-1.step"
        m.m_Offset = pcbnew.VECTOR3D(0, 2.99, 0)   # our pin 1 is 2.99 mm above the S3 footprint's (3D +Y is board up)
        models = [m]
    if name == "USB_C_Receptacle_HRO_TYPE-C-31-M-12":
        # KiCad 10 ships no HRO model; the GCT USB4105 16P top-mount has the same pad row and shield holes (within 0.03 mm)
        m = pcbnew.FP_3DMODEL(); m.m_Filename = "${KICAD10_3DMODEL_DIR}/Connector_USB.3dshapes/USB_C_Receptacle_GCT_USB4105-xx-A_16P_TopMnt_Horizontal.step"
        models = [m]
    if not models:
        if not name.startswith(("Fiducial", "MountingHole")): missing.append(fp.GetReference())
        continue
    fp.Models().clear()
    for m in models:
        n = pcbnew.FP_3DMODEL()
        n.m_Filename = re.sub(r'^.*/jlc\.3dshapes/', JLC_3D, m.m_Filename)
        n.m_Offset, n.m_Rotation, n.m_Scale, n.m_Opacity, n.m_Show = m.m_Offset, m.m_Rotation, m.m_Scale, m.m_Opacity, m.m_Show
        fp.Models().append(n)
    linked += 1
pcbnew.SaveBoard(B, board)
print("3D models linked:", linked, "| without a model:", missing or "none")
