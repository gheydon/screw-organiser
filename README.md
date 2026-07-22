# Parametric Screw Organiser

A parametric remix of the
[PRUSA CORE One screw organizer](https://www.printables.com/model/1324003-prusa-core-one-screw-organizer)
by ooishoo, built with Python and
[build123d](https://build123d.readthedocs.io/). The whole tray is
described by a YAML layout file: rows of bins on a grid, each bin with a
type, a width in grid units, and a label embossed on its ramp. Labels can be
split into separate models for multi-material printing, output is STL or
3MF, and Gridfinity support comes from the
[gridfinity-build123d](https://github.com/Ruudjhuu/gridfinity_build123d)
package.

## Quick start

```sh
uv sync

# multi-material 3MF (default): bins / labels / front as colour-tagged objects
uv run screw-organiser --config layouts/prusa-mmu3-upgrade.yaml

# single combined STL (one colour) instead
uv run screw-organiser --config layouts/prusa-mmu3-upgrade.yaml --format stl

# gridfinity module with magnet pockets; self-stacking tray
uv run screw-organiser --config layouts/prusa-mmu3-upgrade.yaml --gridfinity --magnets
uv run screw-organiser --config layouts/prusa-mmu3-upgrade.yaml --stackable
```

Output lands in `out/` (change with `--out <dir>`). The format decides the
flavour: **3MF is always multi-material**, **STL is always one combined
single-colour file** — there is no separate switch.

A Makefile builds everything in one go: `make` (all layouts as 3MFs),
`make stl`, `make stackable`, `make gridfinity`, `make everything`, or a
single layout with `make prusa-mmu3-upgrade`. Targets rebuild only when the
layout or generator source changes, and `make -j4` parallelises.

### Using the 3MF for multi-material printing

Open `out/<name>.3mf` in PrusaSlicer/OrcaSlicer. When asked whether the
objects should be treated as a single object with multiple parts, say
**yes**, then assign an extruder/filament to the `labels` (bin ramps) and
`front` (front wall text) parts — they are separate so they can be coloured
independently (`colors: { front: ... }` sets the front's display colour).
The labels sit 0.3 mm proud of the ramps and are sunk 0.1 mm into them so
the parts fuse.

## Layout files

A layout describes the tray once; everything else is derived. See
[layouts/prusa-core-one.yaml](layouts/prusa-core-one.yaml) for the full
original and [layouts/example-mixed.yaml](layouts/example-mixed.yaml) for a
small tray mixing bin types. (`.json` layouts are also accepted.)

```yaml
name: my-tray                              # output file basename
frontText: My Screws                       # embossed on the front wall (optional)
tray: { wall: 3, height: 12, floor: 2, cornerRadius: 3.75 }  # Gridfinity-style rounded corners
grid: { pitch: 30, divider: 2 }            # 1 unit = 30 mm; walls between bins 2 mm
defaults: { type: scoop, scoopRadius: 10, rampAngle: 63.435 }
labels: { capHeight: 3.2, depth: 0.3, font: Arial }
colors: { body: "#FA6831", labels: "#1A1A1A" }  # 3MF display colours
binModules:                                # extra bin types, relative to this file
  - ../examples/round_holes.py
rows:                                      # rows[0] is the front row
  - bins:                                  # row depth defaults to 1 unit (units: n for more)
      - { units: 1, label: M3x8, test: true, count: 12 }  # test gauge; count shown with --counts
      - { units: 2, type: deep, label: "Long\nScrews" }   # \n = two-line label
      - { units: 1, type: open }           # no ramp, no label
```

Every row must span the same total number of units. Tray outer size =
`2*wall + units*pitch - divider` per axis — the original is 6×6 units =
184 × 184 mm.

A ramped bin (`scoop`/`deep`) with no `label` key is labelled **Misc**; set
`label: ""` explicitly for a blank ramp. The `open` type has no ramp and is
always unlabelled.

`version: R1` engraves a Prusa-style identification stamp 0.4 mm into the
tray's underside (the centre foot in gridfinity mode) — recessed so the
first layer prints flat, oriented to read when the tray is flipped over.
Tune with `version: { text: R2, capHeight: 6, depth: 0.4 }`, or override at
build time with `--version-text R2`. `--release-text v1.2` stamps a release
tag as a second line beneath the model version (the release workflow does
this automatically with the GitHub release tag).

A bin's `count` records how many pieces belong in it. Counts are not shown
on labels by default; enable them with the `--counts` flag or persistently
with `labels: { showCounts: true }`, which renders e.g. `M3x10 (35)`.

### Test gauges

`test` adds a lying-down gauge groove along the crest of the bin's label
ramp: a head pocket plus a thread channel across the bin width, cut to the
screw's thread length. Lay a candidate screw in it — the head drops into the
pocket, the shoulder butts against the step, and the tip should just reach
the end of the groove, checking diameter and length at once. The channel's
front side opens onto the incline, so the screw is cradled ~120° rather than
enclosed 180° and simply rolls forward out of the gauge. Because the screw
lies flat, any length works regardless of tray height. Leave it off for bins
that don't need it (nuts, couplers, springs, ...).

- `test: true` — size inferred from the label plus thread clearance:
  `M3x8` → 3.4 mm wide x 8 mm long, `2.9x6.5` → 3.3 x 6.5
- `test: M3x16` — explicit thread spec (e.g. when the label covers two
  lengths, gauge the longer one)
- `test: M4` — diameter-only gauge (default gauge length)
- `test: 3.9` — explicit groove width in mm (for imperial sizes the label
  parser can't read, e.g. `6-32`)
- `test: { dia: 3.9, length: 12, head: false }` — fully explicit;
  `head: false` drops the head pocket for grub/set screws.

The head pocket type is an explicit `head` parameter, sized to ISO
dimensions, defaulting to a socket cap:

- `head: cap` — socket head cap screw (SHCS, ISO 4762), **the default**:
  cylindrical pocket ~1.5x thread dia
- `head: button` — button head (BHCS, ISO 7380): wider, shallower cylinder
- `head: flush` — countersunk (FHCS, ISO 10642): a 90-degree conical seat so
  the head nestles flush
- `head: none` (or `false`) — no head pocket, for grub/set screws (and used
  for the headless shaft/spring/PTFE gauges)

`head` can sit inside the `test` dict or alongside it on the bin, e.g.
`{ label: M5x16, test: M5x16, head: button }`. The ISO abbreviations work as
values too (`head: BHCS`). Override the pocket size with `headDia`/`headLength`.

Grooves longer than the bin is wide are clamped — put long screws in a
2+ unit wide bin. Tune globally with `testHoles: { clearance: 0.4, rim: 1.2,
gaugeLength: 10 }` — thread clearance added on inferred specs, shelf rim
around the groove, and the length used for diameter-only gauges.

## Stacking

Two layout switches (also available as CLI flags):

- `stackable: true` (or `--stackable`) — adds a 1.8 mm lip with a 45°
  funnel on top of the walls and a matching 45° chamfer around the bottom
  edge, so identical trays nest and self-centre when stacked. Tune with
  `stacking: { lipHeight: 1.8, mouth: 0.3, chamferClearance: 0.3 }`.
- `gridfinity: true` (or `--gridfinity`) — **experimental** — builds the
  tray as a Gridfinity module using the gridfinity-build123d package:
  `BaseEqual` feet that click into Gridfinity baseplates and the spec
  stacking lip. Bins keep their designed size; the tray rounds up to the
  smallest 42 mm module that holds them and the slack is absorbed by
  proportionally wider dividers and side walls (a 6x6-unit layout becomes a
  5x5 gridfinity module, 209.5 mm). Interior structure is trimmed 0.35 mm so
  stacked modules seat fully. `gridfinity: { half: true }` (or `--half-grid`)
  bases the tray on the 21 mm half grid instead — finer module rounding, so
  less slack in walls and dividers — by patching the package's hardcoded
  42 mm pitch; magnet holes don't fit half-grid feet and are skipped.
  `gridfinity: { magnets: true }` (or
  `--gridfinity --magnets`) adds 6.5 x 2.4 mm magnet pockets to the base
  corners. `gridfinity` implies stacking, so `stackable` is ignored
  alongside it.

## Bin types

Built-ins live in [src/screw_organiser/bins/](src/screw_organiser/bins/):

| type    | shape                                                        |
|---------|--------------------------------------------------------------|
| `scoop` | big front scoop fillet for finger access + labelled ramp (original style) |
| `deep`  | small front fillet, max capacity + labelled ramp             |
| `open`  | plain bin, small fillets, no ramp/label                      |

### Adding your own at runtime

A bin type is a `.py` module exposing `NAME` and
`build(cell, bin_spec, params)` returning `{"cavity": Part, "label": Part | None}`
— the cavity is subtracted from the tray shell, the label is added to the
labels model. List it in the layout's `binModules` and reference it by name —
no changes to this project needed. See
[examples/round_holes.py](examples/round_holes.py), which drills storage
wells into the bin floor:

- `cell` — `{x, y, width, depth}`, the bin's interior floor rectangle in mm
- `bin_spec` — the raw layout entry (your custom options ride along, e.g.
  `holeDiameter`)
- `params` — resolved tray/labels settings (`height`, `floor`, `rampAngle`,
  `scoopRadius`, `labels`, `test`)

Helpers in `screw_organiser.bins.common` (`scoop_cavity`, `ramp_label`,
`test_spec`) do the heavy lifting.

## How it fits together

```
layouts/*.yaml                    tray descriptions (the only thing you normally edit)
src/screw_organiser/cli.py        CLI: args, layout load, export dispatch
src/screw_organiser/layout.py     defaults, YAML/JSON loading, grid validation
src/screw_organiser/tray.py       grid maths, shell, cavity subtraction, modes
src/screw_organiser/bins/         runtime bin-type registry + built-ins
src/screw_organiser/text.py       real-font labels (build123d Text)
src/screw_organiser/stacking.py   stackable lip + bottom chamfer
src/screw_organiser/export.py     STL (export_stl) and 3MF (Mesher, colours)
```

Geometry notes, all parametric: bins are cut as one extruded 2D profile per
bin — front fillet (radius `scoopRadius`, tangent to the wall top and floor),
flat floor, then a `rampAngle` ramp rising to full height, whose face carries
the label. Gridfinity geometry (base feet, magnet holes, stacking lip) comes
from the gridfinity-build123d package: the tray shell is
`Bin(BaseEqual(...), height=..., lip=StackingLip())` with the bins carved
from its solid fill.

## Contributing a tray

Trays for other printers and kits are very welcome — a tray is just a YAML
file. To add one:

1. Copy an existing layout in `layouts/` (e.g. `prusa-mini-kit.yaml`) and
   fill in your rows of bins: `label`, `units` wide, `count`, and `test` for
   screw/shaft/spring gauges. Every row must span the same total units.
2. Aggregate the hardware from the kit's assembly manual — per-step parts
   callouts are the reliable source. Note exclusions (rods, belts, zip ties)
   in a comment at the top, and start it at `version: R1`.
3. `make <your-layout-name>` to build it, check the render/slicer output,
   and open a pull request.

## License

CC0 1.0 (public domain) — see [LICENSE](LICENSE).

This project is a remix of the
[PRUSA CORE One screw organizer](https://www.printables.com/model/1324003-prusa-core-one-screw-organizer)
by ooishoo, published under the same CC0 1.0 licence.
