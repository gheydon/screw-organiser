"""Plain open bin: small fillets front and back, no ramp, no label."""

from .common import scoop_cavity

NAME = "open"
DESCRIPTION = "Plain open bin, no label ramp"


def build(cell, bin_spec, params):
    cavity, _ = scoop_cavity(
        cell, params,
        scoop_radius=bin_spec.get("scoopRadius", 3),
        with_ramp=False,
    )
    return {"cavity": cavity, "label": None}
