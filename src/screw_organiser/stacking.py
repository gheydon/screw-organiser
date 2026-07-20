"""Self-stacking lip / bottom chamfer for non-Gridfinity trays.

Gridfinity mode does not use this module — its base and stacking lip come
from the gridfinity_build123d package.
"""

from __future__ import annotations

from build123d import (
    BuildPart,
    BuildSketch,
    Part,
    Plane,
    RectangleRounded,
    extrude,
    loft,
)


def rounded_plate(width: float, depth: float, corner_r: float, inset: float, z: float):
    """Sketch of the tray outline shrunk by `inset`, on plane z."""
    return (
        Plane.XY.offset(z),
        RectangleRounded(width - 2 * inset, depth - 2 * inset, max(corner_r - inset, 0.3)),
    )


def _sketch(width, depth, corner_r, inset, z):
    with BuildSketch(Plane.XY.offset(z)) as sk:
        RectangleRounded(width - 2 * inset, depth - 2 * inset, max(corner_r - inset, 0.3))
    return sk.sketch


def frustum(width, depth, corner_r, inset_a, za, inset_b, zb) -> Part:
    """45-degree-ish solid lofted between two insets of the tray outline."""
    with BuildPart() as bp:
        loft([
            _sketch(width, depth, corner_r, inset_a, za),
            _sketch(width, depth, corner_r, inset_b, zb),
        ])
    return bp.part


def prism(width, depth, corner_r, inset, z0, z1) -> Part:
    with BuildPart() as bp:
        with BuildSketch(Plane.XY.offset(z0)):
            RectangleRounded(width - 2 * inset, depth - 2 * inset, max(corner_r - inset, 0.3))
        extrude(amount=z1 - z0)
    return bp.part


def stacking_lip(width, depth, corner_r, wall, z0, lip_height, mouth) -> Part:
    """Ring on top of the walls with a 45-degree funnel inside."""
    ring = (
        prism(width, depth, corner_r, 0, z0, z0 + lip_height)
        - prism(width, depth, corner_r, wall, z0 - 1, z0 + lip_height + 1)
    )
    funnel = frustum(width, depth, corner_r, mouth + lip_height, z0 - 0.01, mouth, z0 + lip_height)
    funnel += prism(width, depth, corner_r, mouth, z0 + lip_height - 0.02, z0 + lip_height + 1)
    return ring - funnel


def bottom_nest(width, depth, corner_r, chamfer, total_height) -> Part:
    """Solid to intersect the body with: chamfers the bottom outer edge."""
    keep = frustum(width, depth, corner_r, chamfer, 0, 0, chamfer)
    keep += prism(width, depth, corner_r, 0, chamfer - 0.02, total_height + 1)
    return keep
