"""CLI.

  screw-organiser [--config layouts/prusa-core-one.yaml]
                  [--format 3mf|stl] [--counts]
                  [--stackable] [--gridfinity] [--magnets]
                  [--out out]

3MF output (default) is always multi-material: one colour-tagged object each
for bins, labels and front text. STL output is one combined file.
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

from .export import export
from .layout import load_layout
from .tray import build_tray


def main() -> None:
    ap = argparse.ArgumentParser(description="Parametric screw organiser generator (build123d)")
    ap.add_argument("--config", default="layouts/prusa-core-one.yaml")
    ap.add_argument("--format", choices=["3mf", "stl"], default="3mf",
                    help="3mf: multi-material (bins/labels/front objects); stl: one combined file")
    ap.add_argument("--counts", action="store_true",
                    help='append each bin\'s "count" to its label')
    ap.add_argument("--stackable", action="store_true",
                    help="add stacking lip + bottom chamfer")
    ap.add_argument("--gridfinity", action="store_true",
                    help="build as a Gridfinity module (via gridfinity_build123d) [experimental]")
    ap.add_argument("--magnets", action="store_true",
                    help="with --gridfinity: magnet holes in the base")
    ap.add_argument("--half-grid", action="store_true",
                    help="with --gridfinity: 21 mm half-grid base instead of 42 mm")
    ap.add_argument("--version-text", metavar="TEXT",
                    help='engrave TEXT into the tray underside (overrides layout "version")')
    ap.add_argument("--out", default="out")
    args = ap.parse_args()

    layout, layout_dir = load_layout(args.config)
    if args.counts:
        layout["labels"] = {**layout.get("labels", {}), "showCounts": True}
    if args.stackable:
        layout["stackable"] = True
    if args.gridfinity:
        layout["gridfinity"] = layout.get("gridfinity") or True
    if args.magnets:
        gf = layout.get("gridfinity")
        layout["gridfinity"] = {**(gf if isinstance(gf, dict) else {}), "magnets": True}
    if args.half_grid:
        gf = layout.get("gridfinity")
        layout["gridfinity"] = {**(gf if isinstance(gf, dict) else {}), "half": True}
    if args.version_text:
        layout["version"] = args.version_text

    t0 = time.time()
    print(f'building "{layout.get("name", "organiser")}" from {args.config} ...')
    tray = build_tray(layout, layout_dir)
    w, d, h = tray.size
    print(
        f"  {w:g} x {d:g} x {h:g} mm, {tray.stats['bins']} bins, "
        f"{tray.stats['labels']} labels ({time.time() - t0:.1f} s)"
    )

    for path in export(tray, layout, args.format, Path(args.out)):
        kb = path.stat().st_size / 1024
        print(f"  wrote {path} ({kb:.0f} kB)")
    print(f"done in {time.time() - t0:.1f} s")


if __name__ == "__main__":
    main()
