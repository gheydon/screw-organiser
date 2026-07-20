"""Maximum-capacity variant: small front fillet + labelled back ramp."""

from .common import ramp_label, scoop_cavity, test_spec

NAME = "deep"
DESCRIPTION = "Small front fillet + labelled back ramp (max capacity)"


def build(cell, bin_spec, params):
    cavity, ramp = scoop_cavity(
        cell, params,
        scoop_radius=bin_spec.get("scoopRadius", 3),
        with_ramp=True,
        test=test_spec(bin_spec, params),
    )
    return {"cavity": cavity, "label": ramp_label(cell, bin_spec, params, ramp)}
