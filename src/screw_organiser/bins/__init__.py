"""Runtime bin-type registry.

A bin type is any module exposing NAME and build(cell, bin_spec, params)
returning {"cavity": Part, "label": Part | None}. Built-ins live in this
package; layouts can add their own via "binModules" (paths relative to the
layout file), loaded at runtime.
"""

from __future__ import annotations

import importlib
import importlib.util
from pathlib import Path

_BUILTINS = ("scoop", "deep", "open")
_registry: dict[str, object] = {}


def _register(mod, source: str):
    if not getattr(mod, "NAME", None) or not callable(getattr(mod, "build", None)):
        raise ValueError(f"bin module {source} must expose NAME and build()")
    _registry[mod.NAME] = mod
    return mod


def register_modules(module_list: list[str] | None, base_dir: Path) -> None:
    for rel in module_list or []:
        if not rel.endswith(".py"):
            continue  # e.g. a .js module for the JSCAD implementation
        path = (base_dir / rel).resolve()
        spec = importlib.util.spec_from_file_location(f"binmod_{path.stem}", path)
        if spec is None or spec.loader is None:
            raise ImportError(f"cannot load bin module {path}")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _register(mod, str(path))


def load(type_name: str):
    if type_name in _registry:
        return _registry[type_name]
    if type_name in _BUILTINS:
        mod = importlib.import_module(f".{type_name}", __package__)
        return _register(mod, type_name)
    raise ValueError(f"unknown bin type {type_name!r} (available: {', '.join(available())})")


def available() -> list[str]:
    return sorted(set(_registry) | set(_BUILTINS))
