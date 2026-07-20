"""Original organiser style: front scoop + labelled back ramp."""

from .common import ramp_label, scoop_cavity, test_spec

NAME = "scoop"
DESCRIPTION = "Front scoop fillet + labelled back ramp (original style)"


def build(cell, bin_spec, params):
    cavity, ramp = scoop_cavity(
        cell, params,
        scoop_radius=bin_spec.get("scoopRadius", params["scoopRadius"]),
        with_ramp=True,
        test=test_spec(bin_spec, params),
    )
    return {"cavity": cavity, "label": ramp_label(cell, bin_spec, params, ramp)}
