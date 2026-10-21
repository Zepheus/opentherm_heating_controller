# Layout notes: what worked, what did not (2026-10-20)

Working notes from placing and routing the first revision. The geometry itself
is in `design.md` (Layout and routing); this file records the reasoning and the
dead ends so the next revision does not repeat them.

## Placement decisions and margins

- **Board size over layer count.** 150 × 95 mm 2-layer was chosen over a
  smaller 4-layer board: the 6.4 mm mains-to-SELV band and the 5 mm terminal
  pitch set the size, not the SELV density. JLC 2-layer is also cheaper per
  board than any 4-layer option at a run of five.
- **Mains along one edge, SELV along the opposite edge**, with the relays and
  optos as the only parts bridging the isolation band. This makes the DRC
  rule set simple: one polygon rule area plus net classes.
- **JLC assembly margins that bit:** courtyards must sit inside the outline.
  The two right-edge terminal blocks (J115/J116) were first placed with their
  body 1 mm over the edge and only the courtyard check caught it; they moved
  from x 146 to 143.5. Rule: run a courtyard-vs-outline check before routing,
  the renders do not show it clearly.
- **Buttons ≥ 9 mm from the edge** (user wants them hidden inside the lid);
  fiducials in the SELV region only (silk/fiducial rule inside the band);
  mounting holes as a corner rectangle ≥ 6.4 mm from mains copper.
- **Sense-chain columns**: 1206 resistors in two columns per channel with
  the opto at the bottom of the band. The last resistor's own pads sit ~1.3 mm
  apart across the N node, so any mains-to-sense rule above 1.3 mm for chain
  nodes is impossible to satisfy with 1206 parts. Raw live inputs are a
  separate class (MAINS_IN, 2.0 mm).
- **USB-C pad row** (0.5 mm pitch, interleaved D+/D−) cannot be left to the
  autorouter: fixed bridges (D− inner, D+ outer) and VBUS escapes that pass the
  locating holes with ≥ 0.25 mm hole clearance were laid by hand and locked.

## Routing pipeline: what worked

- Freerouting 2.5 headless from a KiCad DSN, 40 passes, ~1 min. Result:
  12 "unrouted" internally (locked nets and GND left to pours), 0 unconnected
  in KiCad.
- **Pre-route everything an autorouter cannot be trusted with and lock it**:
  L and N buses, relay COM/NO links, DEMAND_RET return, USB bridges, VBUS,
  and GND stitching vias. Locked tracks export as fixed wiring and survive the
  SES import.
- **Temporary rule areas** steer the router: a bus corridor keepout on each
  layer so sense tracks do not wander into the mains strip, and 2.2 mm edge
  guards around the 230 V region. Removed after the SES import.
- **Strip and re-add mains copper** after the SES import: the DSN/SES round
  trip rewrites locked segments, so the script deletes every MAINS segment and
  via by text and re-lays the buses deterministically.
- **GND stitching vias on a 10 mm grid before routing** keep the bottom pour
  in one piece. Without them long bottom tracks along the isolation band cut
  the pour into islands that KiCad removed silently; the bottom pour was
  3144 mm² instead of 4397 mm² and nothing in DRC said so.
- **Gap closer**: the SES import occasionally leaves sub-millimetre same-net
  gaps that DRC reports as unconnected; a text pass closes them.
- **Inset outline 0.15 mm for the router** so its own edge clearance lands on
  the real edge; restore the true outline and cut the slots afterwards.
- Pour the 3V3 copper for the regulator tab **before** routing so the router
  treats it as an obstacle; added afterwards it fragments to a third of its
  area around other nets' tracks.

## Routing pipeline: what did not work

- **Konnect IPC for the pipeline**: the editor must be closed for file
  rewrites, and the user's open editor goes stale. The pipeline therefore
  works on files and the editor is reopened afterwards.
- **pcbnew Python SWIG quirks** (KiCad 10.0.7): footprint proxies from
  `board.Footprints()` go stale after board edits in the same process
  (`GetCourtyard` attribute errors); iterate footprints first and cache what
  is needed. `GetSettingsManager().LoadProject` must precede `LoadBoard` for
  net classes and must be called once per process. Running the KiCad Python
  **without `-I`** let user site-packages in and segfaulted the prep stage
  intermittently; always `python3 -I`.
- **A child KiCad Python process from inside KiCad Python** (subprocess for
  courtyard lookup) corrupted the parent (duplicate zones, segfault). Do not.
- **Hole clearance at the USB connector**: the VBUS stubs first ran 0.12 mm
  from the NPTH locating holes; moving them outward too early clipped the
  SBU/CC pads instead. The working path exits each VBUS pad straight down past
  the pad row, then steps outward.
- **Corridor keepouts that reach the terminal pads** trap them: after moving
  J116 to x 143.5 the DEMAND inputs could not escape until the corridor was
  trimmed to x 138.
- **Hand-laid DEMAND_RET before the inputs were fixed** got crossed by the
  router; the fix was to lay all mains links as fixed wiring before routing
  rather than after.
- **Zone fills are DRC-silent**: lost pour area, fragmented pours and islands
  produce no DRC item. Check filled area per zone in a script after every run.
- **Render colours**: `kicad-cli pcb render --background white` is rejected
  in 10.0.7; omit the option.

## Round-2 routing lessons (after the independent review)

- **Freerouting ignores copper zones as obstacles.** A +3V3 pour laid before
  routing came back fragmented to 40 mm² because other nets were routed
  straight through it. What works: a temporary rule area (no tracks, no vias)
  on that layer during routing, removed after the SES import, then the pour.
- **A rule-area keepout that covers any pad of a net blocks that whole net.**
  Trying the keepout trick for the regulator pour (the SOT-223 tab sits inside
  it) made Freerouting abandon all 44 +3V3 connections. What works instead:
  locked +3V3 copper bars (2.5 mm tracks) laid where the pour will be; other
  nets route around them, +3V3 attaches to them, and the pour fills the rest.
- **A clearance rule larger than a part's own pad gap is unroutable.** With
  the raw live inputs at 2.0 mm, the input resistor's two 1206 pads (1.8 mm
  apart) conflict with each other and Freerouting cannot even enter the pad.
  Fix: a locked 0.5 mm exit stub from the pad to 2.5 mm away, plus a DRC rule
  that allows 1.3 mm between that net and its own first chain node only
  (38 V across that resistor). Rules are evaluated last-match-wins, so the
  exemption goes after the general rule.
- **A 2.0 mm class in a 0.5 mm-clearance neighbourhood is a hand-routing
  job.** With exit stubs the router still reached only two of the four raw
  live inputs; the lanes to the terminals (between the N-drop vias, the
  DEMAND_RET return and the terminal pads) have one legal position each.
  They are now fully pre-routed and locked, which also makes the result
  deterministic. The bottom bus corridor had to shrink to y ≤ 21.5 to free
  the lane region; the 2.0 mm rules protect the N-drop vias instead.
- **GND by pour alone is fragile on 2 layers.** Once the router had to use
  more bottom-layer copper (2.0 mm lanes, locked bars), the pours split into
  islands around the USB connector, regulator and optos, each holding GND
  pads with no path to the main ground. DRC reports these as zone-to-zone
  unconnected items. The pipeline now repairs them: for every island that
  holds a pad it drops a GND via where the other layer's main pour lies
  underneath, refills, and repeats. Locked copper bars in a busy corridor
  (the lower regulator bar between USB and the OT terminal) made this much
  worse and were removed; 60 router passes took 29 minutes without helping,
  40 is the right number.
- **Zone islands**: set island removal to ALWAYS explicitly on zones created
  from Python; the default left islands that DRC then reports as
  unconnected.
- **Raising mains-to-mains from 1.4 to 2.0 mm** cost one pre-route change:
  the L drop moved from x 131 to 130.6 with a 2.0 mm bottom track and 1.2 mm
  vias; the N drop next to it stays. Check every via/track pair of the
  hand-laid buses against the rule before blaming the router.
- **Net changes without the editor.** "Update PCB from schematic" needs the
  GUI; a 50-line pcbnew script that sets pad nets, values, DNP attribute and
  copies LCSC/Description/Datasheet fields does the same, verified with
  `kicad-cli pcb drc --schematic-parity` (only the 7 board-only holes and
  fiducials should remain).
- **Easyeda2kicad is not always available** for a part (API refused the fuse);
  KiCad's own library had an equivalent package (nano² 451/453 = 2410).

## Review lessons

- The first independent review found two "confirmed" OpenTherm wiring
  errors; one was a misread of the reference, the other a real net merge.
  Re-derive every reference comparison pin by pin from the source image
  before accepting or rejecting; both sides got something wrong.
- Documentation drifted from the files in six places (layer policy, track
  width, resistor split, headroom, part names, component count). Treat the
  design doc as a deliverable that is diffed against the netlist, not prose.
- A detector-margin argument made with peak currents was wrong; a 20-line
  time-domain model settled it in seconds. Model the periodic steady state.
