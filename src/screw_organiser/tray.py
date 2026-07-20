"""Tray assembly: grid maths, shell, cavity subtraction, labels, modes.

Coordinate system matches the JSCAD implementation: origin at the tray's
front-left-bottom corner; X = columns, Y = rows (row 0 at the front),
Z = height.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import reduce
from operator import add
from pathlib import Path

from build123d import Part, Pos, Rot

from . import bins as bin_registry
from .bins.common import shelf_for, test_spec
from .layout import DEFAULTS, merged, validate_rows
from .stacking import bottom_nest, stacking_lip
from .text import solid_label

GF_WALL = 2.6  # wall thickness needed behind the gridfinity stacking lip
GF_INTERIOR_TRIM = 0.35  # stacked feet reach this far below the wall top


@dataclass
class Tray:
    name: str
    size: tuple[float, float, float]
    body: Part
    labels: list[Part] = field(default_factory=list)
    front: list[Part] = field(default_factory=list)
    stats: dict = field(default_factory=dict)


def build_tray(layout: dict, layout_dir: Path) -> Tray:
    tray = merged(DEFAULTS["tray"], layout.get("tray"))
    grid = merged(DEFAULTS["grid"], layout.get("grid"))
    bin_defaults = merged(DEFAULTS["bin"], layout.get("defaults"))
    labels_cfg = merged(DEFAULTS["labels"], layout.get("labels"))
    stacking_cfg = merged(DEFAULTS["stacking"], layout.get("stacking"))

    gridfinity = bool(layout.get("gridfinity"))
    gf_opts = layout["gridfinity"] if isinstance(layout.get("gridfinity"), dict) else {}
    stackable = bool(layout.get("stackable")) and not gridfinity
    if gridfinity:
        print("  note: gridfinity mode is experimental — check fit before a long print")

    bin_registry.register_modules(layout.get("binModules"), layout_dir)
    cols, rows_deep = validate_rows(layout)

    wall = tray["wall"]
    if gridfinity and (layout.get("tray", {}).get("wall") is None or wall < GF_WALL):
        wall = GF_WALL

    # ---- shell + outer dimensions -------------------------------------
    base_h = 0.0
    lip_h = 0.0
    if gridfinity:
        # Bins keep their designed size (pitch - divider content per unit);
        # the tray rounds up to the next 42 mm gridfinity module and the
        # slack is absorbed by proportionally wider dividers and side walls.
        import math

        gf_pitch = 21 if gf_opts.get("half") else 42
        unit_x = grid["pitch"] - grid["divider"]
        unit_y = grid["pitch"] - grid["divider"]
        need_x = cols * unit_x + (cols - 1) * grid["divider"] + 2 * wall
        need_y = rows_deep * unit_y + (rows_deep - 1) * grid["divider"] + 2 * wall
        gx = math.ceil((need_x + 0.5) / gf_pitch)
        gy = math.ceil((need_y + 0.5) / gf_pitch)
        print(f"  gridfinity module: {gx} x {gy} ({gf_pitch} mm units)")
        # version stamp goes on the underside of the centre-most foot
        footprint = gf_pitch - 0.5
        stamp_cx = ((gx - 1) // 2) * gf_pitch + footprint / 2
        stamp_cy = ((gy - 1) // 2) * gf_pitch + footprint / 2
        stamp_w = footprint - 2 * 2.95 - 3  # foot bottom face minus a margin

        shell, width, depth, base_h, lip_h, corner_r = _gridfinity_shell(
            gx, gy, tray["height"], gf_opts
        )
        kx = (width - cols * unit_x) / (2 * wall + (cols - 1) * grid["divider"])
        ky = (depth - rows_deep * unit_y) / (2 * wall + (rows_deep - 1) * grid["divider"])
        wall_x, div_x = wall * kx, grid["divider"] * kx
        wall_y, div_y = wall * ky, grid["divider"] * ky
        pitch_x = unit_x + div_x
        pitch_y = unit_y + div_y
    else:
        width = wall * 2 + cols * grid["pitch"] - grid["divider"]
        depth = wall * 2 + rows_deep * grid["pitch"] - grid["divider"]
        corner_r = layout.get("tray", {}).get(
            "cornerRadius", layout.get("tray", {}).get("cornerChamfer", tray["cornerRadius"])
        )
        shell = Pos(width / 2, depth / 2, 0) * prism_centered(width, depth, corner_r, tray["height"])
        wall_x = wall_y = wall
        div_x = div_y = grid["divider"]
        pitch_x = pitch_y = grid["pitch"]
        stamp_cx, stamp_cy = width / 2, depth / 2
        stamp_w = width / 2

    params = {
        "height": base_h + tray["height"],
        "floor": base_h + tray["floor"],
        "rampAngle": bin_defaults["rampAngle"],
        "scoopRadius": bin_defaults["scoopRadius"],
        "labels": labels_cfg,
        "test": merged(DEFAULTS["test"], layout.get("testHoles")),
    }

    # ---- bins ---------------------------------------------------------
    cavities: list[Part] = []
    labels: list[Part] = []
    bin_count = 0

    row_start = 0
    for row in layout["rows"]:
        row_deep = row.get("units", 1)
        # rows containing a gauge get one shelf depth (the largest needed)
        # applied to every bin, so all ramps in the row line up
        row_shelf = 0.0
        for bin_spec in row["bins"]:
            spec = test_spec(bin_spec, params)
            if spec:
                row_shelf = max(row_shelf, shelf_for(spec, params))
        col_start = 0
        for bin_spec in row["bins"]:
            units = bin_spec.get("units", 1)
            cell = {
                "x": wall_x + col_start * pitch_x,
                "y": wall_y + row_start * pitch_y,
                "width": units * pitch_x - div_x,
                "depth": row_deep * pitch_y - div_y,
                "shelf": row_shelf,
            }
            mod = bin_registry.load(bin_spec.get("type", bin_defaults["type"]))
            result = mod.build(cell, bin_spec, params)
            if result.get("cavity") is not None:
                cavities.append(result["cavity"])
            if result.get("label") is not None:
                labels.append(result["label"])
            bin_count += 1
            col_start += units
        row_start += row_deep

    # ---- front text ----------------------------------------------------
    nest_chamfer = (
        stacking_cfg["mouth"] + stacking_cfg["lipHeight"] + stacking_cfg["chamferClearance"]
        if stackable else 0.0
    )
    front: list[Part] = []
    if layout.get("frontText"):
        spec = layout["frontText"]
        spec = {"text": spec} if isinstance(spec, str) else spec
        cfg = merged(DEFAULTS["frontText"], spec)
        solid = solid_label(
            spec["text"],
            cap_height=cfg["capHeight"],
            depth=cfg["depth"] + labels_cfg["overlap"],
            max_width=width - 2 * corner_r - 6,
            font=labels_cfg["font"],
        )
        # centre on the visible face: above the bottom nesting chamfer and
        # including the stacking lip when present
        face_top = tray["height"] + (stacking_cfg["lipHeight"] if stackable else 0.0)
        front_z = base_h + (nest_chamfer + face_top) / 2
        front.append(
            Pos(width / 2, labels_cfg["overlap"], front_z)
            * Rot(90, 0, 0)
            * solid
        )

    # ---- assemble ------------------------------------------------------
    body = shell - reduce(add, cavities) if cavities else shell

    total_height = base_h + tray["height"] + lip_h
    if stackable:
        nest = Pos(width / 2, depth / 2, 0) * bottom_nest(width, depth, corner_r, nest_chamfer, tray["height"])
        lip = Pos(width / 2, depth / 2, 0) * stacking_lip(
            width, depth, corner_r, wall, tray["height"],
            stacking_cfg["lipHeight"], stacking_cfg["mouth"],
        )
        body = (body & nest) + lip
        total_height += stacking_cfg["lipHeight"]

    if gridfinity:
        # trim interior structure so stacked feet seat in the lip
        trim = Pos(width / 2, depth / 2, params["height"] - GF_INTERIOR_TRIM) * prism_centered(
            width - 2 * min(wall_x, wall_y), depth - 2 * min(wall_x, wall_y),
            max(corner_r - min(wall_x, wall_y), 0.3), 2
        )
        body -= trim

    # ---- version stamp -------------------------------------------------
    # Engraved into the underside (Prusa-style part identification). The
    # text is mirrored so it reads correctly when the tray is flipped over,
    # and recessed so the first layer prints flat.
    if layout.get("version"):
        spec = layout["version"]
        spec = {"text": str(spec)} if not isinstance(spec, dict) else spec
        cfg = merged(DEFAULTS["versionText"], spec)
        stamp = solid_label(
            str(spec["text"]),
            cap_height=cfg["capHeight"],
            depth=cfg["depth"] + 0.01,
            max_width=stamp_w,
            font=labels_cfg["font"],
        )
        body -= Pos(stamp_cx, stamp_cy, cfg["depth"]) * Rot(180, 0, 0) * stamp

    return Tray(
        name=layout.get("name", "organiser"),
        size=(width, depth, total_height),
        body=body,
        labels=labels,
        front=front,
        stats={
            "bins": bin_count,
            "labels": len(labels) + len(front),
            "cols": cols,
            "rows": len(layout["rows"]),
            "gridfinity": gridfinity,
            "stackable": stackable,
        },
    )


def prism_centered(width: float, depth: float, corner_r: float, height: float) -> Part:
    """Rounded-corner block centred on XY origin, sitting on z=0."""
    from build123d import BuildPart, BuildSketch, RectangleRounded, extrude

    with BuildPart() as bp:
        with BuildSketch():
            RectangleRounded(width, depth, corner_r)
        extrude(amount=height)
    return bp.part


def _gridfinity_shell(cols: int, rows: int, body_height: float, gf_opts: dict):
    """Solid gridfinity shell (base + fill + stacking lip) in corner frame.

    With gf_opts["half"], the base is generated on the 21 mm half grid. The
    package hardcodes the 42 mm pitch as a module constant, so it is patched
    for the duration of the base build (the foot profile, corner radius and
    clearance are absolute and unaffected, per the half-grid spec).
    """
    from gridfinity_build123d import BaseEqual, Bin, BottomCorners, MagnetHole, StackingLip
    from gridfinity_build123d.constants import gridfinity_standard

    half = bool(gf_opts.get("half"))
    magnets = bool(gf_opts.get("magnets"))
    if half and magnets:
        # 6.5 mm magnet holes 8 mm from each side would overlap on a 21 mm foot
        print("  note: magnet holes don't fit the 21 mm half grid — skipped")
        magnets = False

    features = [MagnetHole(BottomCorners())] if magnets else []
    original_pitch = gridfinity_standard.grid.size
    gridfinity_standard.grid.size = 21 if half else 42
    try:
        base = BaseEqual(grid_x=cols, grid_y=rows, features=features)
        base_h = base.bounding_box().size.Z
        shell = Bin(base, height=body_height, lip=StackingLip())
    finally:
        gridfinity_standard.grid.size = original_pitch

    bb = shell.bounding_box()
    width, depth = bb.size.X, bb.size.Y
    lip_h = bb.size.Z - base_h - body_height
    corner_r = 3.75  # bin outer corner radius (grid radius 4 - tolerance/2)

    shell = Pos(-bb.min.X, -bb.min.Y, -bb.min.Z) * shell
    return shell, width, depth, base_h, lip_h, corner_r
