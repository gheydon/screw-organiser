"""Solid label text via build123d's real-font Text sketches."""

from __future__ import annotations

from functools import lru_cache

from build123d import (
    Align,
    BuildSketch,
    Locations,
    Part,
    Pos,
    Text,
    extrude,
)


@lru_cache(maxsize=8)
def _cap_factor(font: str) -> float:
    """Ratio of rendered uppercase height to font_size for this font."""
    with BuildSketch() as sk:
        Text("X", font_size=10, font=font, align=(Align.CENTER, Align.CENTER))
    return sk.sketch.bounding_box().size.Y / 10


def _build_sketch(lines: list[str], font_size: float, spacing: float, font: str):
    with BuildSketch() as sk:
        n = len(lines)
        for i, line in enumerate(lines):
            y = ((n - 1) / 2 - i) * spacing
            with Locations((0, y)):
                Text(line, font_size=font_size, font=font, align=(Align.CENTER, Align.CENTER))
    return sk.sketch


def solid_label(
    text: str,
    cap_height: float = 3.2,
    depth: float = 0.3,
    line_spacing: float = 1.4,
    max_width: float | None = None,
    font: str = "Arial",
) -> Part:
    """Label lying in the XY plane, extruded 0..depth, centred on the origin.

    Glyphs shrink uniformly if the text would exceed max_width.
    """
    lines = text.split("\n")
    size = cap_height / _cap_factor(font)
    sketch = _build_sketch(lines, size, cap_height * line_spacing, font)

    if max_width:
        w = sketch.bounding_box().size.X
        if w > max_width:
            s = max_width / w
            sketch = _build_sketch(lines, size * s, cap_height * s * line_spacing, font)

    # centre on the overall bounding box (multi-line stacks may be asymmetric)
    bb = sketch.bounding_box()
    sketch = Pos(-bb.center().X, -bb.center().Y, 0) * sketch
    return extrude(sketch, amount=depth)
