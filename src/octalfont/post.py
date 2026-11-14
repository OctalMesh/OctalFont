"""Binary post-processing that gftools does not cover."""

from __future__ import annotations

from pathlib import Path

from fontTools.ttLib import TTFont, newTable


def add_meta(path: Path, scripts: list[str]) -> None:
    """Add the ``meta`` table with design/supported language tags (``dlng``/``slng``)."""

    with TTFont(path) as font:
        meta = newTable("meta")
        meta.data = {"dlng": ", ".join(scripts), "slng": ", ".join(scripts)}
        font["meta"] = meta

        font.save(path)
