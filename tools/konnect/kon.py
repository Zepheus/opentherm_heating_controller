#!/usr/bin/env python3
"""kon.py <outfile.json> <tool> <args.json|@file> [...]: run Konnect MCP tools over stdio without an MCP client; saves the results (parsed JSON where possible). Loads the schematic and PCB toolsets first. KONNECT env var overrides the binary."""
import sys, json, subprocess, os, shutil
out = sys.argv[1]
calls = [(sys.argv[i], json.loads(sys.argv[i+1]) if not sys.argv[i+1].startswith("@") else json.load(open(sys.argv[i+1][1:]))) for i in range(2, len(sys.argv), 2)]
msgs = [{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"kon","version":"0"}}},
        {"jsonrpc":"2.0","method":"notifications/initialized"},
        {"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"load_toolset","arguments":{"name":["sch_components","sch_wiring","sch_batch","sch_analysis","sch_export","sch_hierarchy","library","pcb_board","pcb_components","pcb_routing","verification","pcb_export"]}}}]
for n,(t,a) in enumerate(calls, start=10):
    msgs.append({"jsonrpc":"2.0","id":n,"method":"tools/call","params":{"name":t,"arguments":a}})
p = subprocess.run([os.environ.get("KONNECT", shutil.which("konnect") or os.path.expanduser("~/.local/bin/konnect"))], input="\n".join(json.dumps(m) for m in msgs)+"\n", capture_output=True, text=True, timeout=300)
results = []
for line in p.stdout.splitlines():
    try: m = json.loads(line)
    except Exception: continue
    if m.get("id",0) >= 10:
        r = m.get("result") or {"error": m.get("error")}
        txt = "".join(c.get("text","") for c in r.get("content",[])) if isinstance(r,dict) and "content" in r else json.dumps(r)
        try: parsed = json.loads(txt)
        except Exception: parsed = txt
        results.append({"tool": calls[m["id"]-10][0], "result": parsed})
json.dump(results, open(out,"w"), indent=1)
for r in results:
    s = json.dumps(r["result"]); print(f"== {r['tool']}: {s[:700]}")
