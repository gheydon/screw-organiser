"""STL and 3MF export for tray parts.

The 3MF is written directly (zip + XML) rather than via build123d's Mesher,
which emits one object per disjoint solid — a tray of labels would become
hundreds of slicer parts. Here each group (bins / labels / front) is
tessellated into exactly one colour-tagged mesh object.
"""

from __future__ import annotations

import zipfile
from pathlib import Path

from build123d import Compound, Part, export_stl

from .tray import Tray

_TOL = 0.01
_ANG_TOL = 0.3

_CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
 <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
 <Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>
</Types>"""

_RELS = """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
 <Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>
</Relationships>"""


def _merged(parts: list[Part]) -> Part | Compound:
    return parts[0] if len(parts) == 1 else Compound(children=list(parts))


def _mesh(shape) -> tuple[list, list]:
    """Tessellate a shape into one welded vertex/triangle mesh."""
    verts, tris = shape.tessellate(_TOL, _ANG_TOL)
    index: dict[tuple, int] = {}
    remap: list[int] = []
    out_verts: list[tuple] = []
    for v in verts:
        key = (round(v.X, 4), round(v.Y, 4), round(v.Z, 4))
        if key not in index:
            index[key] = len(out_verts)
            out_verts.append(key)
        remap.append(index[key])
    out_tris = []
    for a, b, c in tris:
        a, b, c = remap[a], remap[b], remap[c]
        if a != b and b != c and c != a:
            out_tris.append((a, b, c))
    return out_verts, out_tris


def _write_3mf(path: Path, objects: list[tuple[str, str, object]], title: str) -> None:
    """objects: list of (name, hex_color, shape)."""
    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<model unit="millimeter" xml:lang="en-US" '
        'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02" '
        'xmlns:m="http://schemas.microsoft.com/3dmanufacturing/material/2015/02">\n'
        f" <metadata name=\"Title\">{title}</metadata>\n"
        " <resources>\n"
        '  <basematerials id="1">\n'
    ]
    for name, color, _ in objects:
        parts.append(f'   <base name="{name}" displaycolor="{color}"/>\n')
    parts.append("  </basematerials>\n")

    for i, (name, _, shape) in enumerate(objects):
        verts, tris = _mesh(shape)
        parts.append(
            f'  <object id="{i + 2}" type="model" name="{name}" pid="1" pindex="{i}">\n'
            "   <mesh>\n    <vertices>\n"
        )
        parts.extend(f'     <vertex x="{v[0]:g}" y="{v[1]:g}" z="{v[2]:g}"/>\n' for v in verts)
        parts.append("    </vertices>\n    <triangles>\n")
        parts.extend(f'     <triangle v1="{t[0]}" v2="{t[1]}" v3="{t[2]}"/>\n' for t in tris)
        parts.append("    </triangles>\n   </mesh>\n  </object>\n")

    parts.append(" </resources>\n <build>\n")
    parts.extend(f'  <item objectid="{i + 2}"/>\n' for i in range(len(objects)))
    parts.append(" </build>\n</model>\n")

    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", _CONTENT_TYPES)
        z.writestr("_rels/.rels", _RELS)
        z.writestr("3D/3dmodel.model", "".join(parts))


def export(tray: Tray, layout: dict, fmt: str, out_dir: Path) -> list[Path]:
    """STL -> one combined single-colour file; 3MF -> multi-material file
    with one colour-tagged object per group (bins / labels / front)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    base = out_dir / tray.name
    colors = layout.get("colors", {})
    body_c = colors.get("body", "#FA6831")
    label_c = colors.get("labels", "#1A1A1A")
    front_c = colors.get("front", label_c)

    if fmt == "stl":
        path = Path(f"{base}.stl")
        export_stl(_merged([tray.body, *tray.labels, *tray.front]), str(path),
                   tolerance=_TOL, angular_tolerance=_ANG_TOL)
        return [path]

    objects = [("bins", body_c, tray.body)]
    if tray.labels:
        objects.append(("labels", label_c, _merged(tray.labels)))
    if tray.front:
        objects.append(("front", front_c, _merged(tray.front)))
    path = Path(f"{base}.3mf")
    _write_3mf(path, objects, tray.name)
    return [path]
