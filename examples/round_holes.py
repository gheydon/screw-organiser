"""Example custom bin type for the build123d implementation.

A parts-tester bin: flat floor drilled with a row of cylindrical wells,
labelled ramp at the back. Referenced from layouts via "binModules".
External modules import shared helpers from screw_organiser.bins.common.
"""

from build123d import Cylinder, Pos

from screw_organiser.bins.common import ramp_label, scoop_cavity, test_spec

NAME = "round-holes"
DESCRIPTION = "Flat bin with a row of cylindrical wells in the floor"


def build(cell, bin_spec, params):
    cavity, ramp = scoop_cavity(
        cell, params,
        scoop_radius=bin_spec.get("scoopRadius", 3),
        with_ramp="label" not in bin_spec or bin_spec["label"] is not None,
        test=test_spec(bin_spec, params),
    )

    hole_r = bin_spec.get("holeDiameter", 8) / 2
    spacing = hole_r * 2 + 4
    count = max(1, int((cell["width"] - 4) // spacing))
    x0 = cell["x"] + cell["width"] / 2 - (count - 1) * spacing / 2

    skin = 0.8  # floor thickness left under each well
    top = params["floor"] + 1
    for i in range(count):
        cavity += Pos(x0 + i * spacing, cell["y"] + cell["depth"] / 2, (skin + top) / 2) * Cylinder(
            radius=hole_r, height=top - skin
        )

    return {"cavity": cavity, "label": ramp_label(cell, bin_spec, params, ramp)}
