"""Layout loading, defaults and grid maths.

The JSON schema is shared with the original JSCAD implementation, so all
files in layouts/ work unchanged.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

DEFAULTS: dict[str, dict[str, Any]] = {
    "tray": {"wall": 3.0, "height": 12.0, "floor": 2.0, "cornerRadius": 3.75},
    "grid": {"pitch": 30.0, "divider": 2.0},
    "bin": {"type": "scoop", "scoopRadius": 10.0, "rampAngle": 63.435},
    "labels": {
        "capHeight": 3.2,
        "depth": 0.3,
        "overlap": 0.1,
        "lineSpacing": 1.4,
        "showCounts": False,
        "font": "Arial",
    },
    "test": {"clearance": 0.4, "rim": 1.2, "gaugeLength": 10.0},
    "frontText": {"capHeight": 6.0, "depth": 0.3},
    "versionText": {"capHeight": 6.0, "depth": 0.4},
    "stacking": {"lipHeight": 1.8, "mouth": 0.3, "chamferClearance": 0.3},
}


def merged(base: dict, over: dict | None) -> dict:
    return {**base, **(over or {})}


def load_layout(path: str | Path) -> tuple[dict, Path]:
    p = Path(path).resolve()
    with p.open() as f:
        if p.suffix in (".yaml", ".yml"):
            return yaml.safe_load(f), p.parent
        return json.load(f), p.parent


def row_units(row: dict) -> int:
    return sum(b.get("units", 1) for b in row["bins"])


def validate_rows(layout: dict) -> tuple[int, int]:
    """Return (cols, rows_deep); raise on ragged rows."""
    rows = layout.get("rows")
    if not rows:
        raise ValueError("layout has no rows")
    cols = row_units(rows[0])
    for i, row in enumerate(rows):
        if row_units(row) != cols:
            raise ValueError(f"row {i} spans {row_units(row)} units, expected {cols}")
    rows_deep = sum(r.get("units", 1) for r in rows)
    return cols, rows_deep
