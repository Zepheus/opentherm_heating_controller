#!/usr/bin/env python3
"""Append net labels to a KiCad schematic at component pin endpoints.
usage: labeler.py <schematic.kicad_sch> <pins.json> <netmap.json>
pins.json: Konnect batch_get_schematic_pin_locations output
netmap.json: {"REF": {"pin": "NET" | ["NET","hier"|"global"|"local"], ...}, ...}
"""
import sys, json, uuid, re
sch, pins_path, map_path = sys.argv[1:4]
pins = json.load(open(pins_path))
netmap = json.load(open(map_path))
# normalise konnect output -> {ref: {pin_number: (x,y,orient)}}
loc = {}
comps = pins.get("components") or pins.get("results") or pins
if isinstance(comps, dict):
    items = comps.items()
else:
    items = [(c.get("reference"), c) for c in comps]
for ref, c in items:
    plist = c.get("pins") if isinstance(c, dict) else c
    if isinstance(plist, dict):
        plist = [dict(number=k, **v) for k, v in plist.items()]
    d = {}
    for p in plist:
        num = str(p.get("number") or p.get("pin_number") or p.get("pin"))
        x = p.get("x"); y = p.get("y")
        if x is None and "position" in p: x, y = p["position"]["x"], p["position"]["y"]
        if x is None and "endpoint" in p: x, y = p["endpoint"]["x"], p["endpoint"]["y"]
        o = p.get("orientation_degrees", 0)
        d[num] = (float(x), float(y), float(o))
    loc[ref] = d
out = []
missing = []
for ref, pm in netmap.items():
    for pin, spec in pm.items():
        if isinstance(spec, str): net, kind = spec, "local"
        else: net, kind = spec[0], (spec[1] if len(spec) > 1 else "local")
        if ref not in loc or str(pin) not in loc[ref]:
            missing.append(f"{ref}.{pin}"); continue
        x, y, o = loc[ref][str(pin)]
        if net == "NC":
            out.append(f'\t(no_connect\n\t\t(at {x:.2f} {y:.2f})\n\t\t(uuid "{uuid.uuid4()}")\n\t)\n'); continue
        o = int(round(o)) % 360
        rot = {0: 0, 90: 90, 180: 180, 270: 270}[o]
        # KiCad: label rotation 0 reads to the right from the anchor, 180 reads to the left.
        if kind == "local":
            just = {0: "left bottom", 90: "left bottom", 180: "right bottom", 270: "right bottom"}[rot]
            out.append(f'\t(label "{net}"\n\t\t(at {x:.2f} {y:.2f} {rot})\n\t\t(effects\n\t\t\t(font\n\t\t\t\t(size 1.27 1.27)\n\t\t\t)\n\t\t\t(justify {just})\n\t\t)\n\t\t(uuid "{uuid.uuid4()}")\n\t)\n')
        else:
            kw = "hierarchical_label" if kind == "hier" else "global_label"
            shape = "bidirectional" if kind == "hier" else "passive"
            if isinstance(spec, list) and len(spec) > 2: shape = spec[2]
            just = {0: "left", 90: "left", 180: "right", 270: "right"}[rot]
            out.append(f'\t({kw} "{net}"\n\t\t(shape {shape})\n\t\t(at {x:.2f} {y:.2f} {rot})\n\t\t(effects\n\t\t\t(font\n\t\t\t\t(size 1.27 1.27)\n\t\t\t)\n\t\t\t(justify {just})\n\t\t)\n\t\t(uuid "{uuid.uuid4()}")\n\t)\n')
s = open(sch).read()
idx = s.rstrip().rfind(")")
s = s[:idx] + "".join(out) + s[idx:]
open(sch, "w").write(s)
print(f"labels added: {len(out)}; missing pins: {missing}")
