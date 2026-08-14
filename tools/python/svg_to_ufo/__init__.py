"""SVG glyph sources to UFO master pipeline.

Typical usage:

    from svg_to_ufo import build_ufo, build_designspace
    from svg_to_ufo.metrics import load_metrics

    metrics = load_metrics(family_dir)
    ufo = build_ufo(family_dir, "Regular", metrics)
    build_designspace(family_dir, {"Regular": ufo}, metrics)
"""

from svg_to_ufo.ufo.builder import build_ufo
from svg_to_ufo.ufo.designspace import build_designspace
from svg_to_ufo.cli import main

__all__ = ["build_ufo", "build_designspace", "main"]
