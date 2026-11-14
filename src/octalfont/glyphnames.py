"""Glyph naming and glyph-set data.

SVG file stems use GF *nice names* (``Zhe-cy``, ``guillemetleft``,
``caroncomb.alt``), which glyphsLib resolves to codepoints, categories and
production names. This replaces the hand-maintained filename table.

Glyph-set definitions (``GF_Latin_Core`` ...) are FROZEN copies shipped in
``octalfont/data/glyphsets``: the upstream ``glyphsets`` package changed what
``GF_Cyrillic_Plus`` means between releases (284 -> 93 glyphs), and a font
under development must not shift targets silently. A project may add or
override sets in ``sources/glyphsets/<Name>.nam`` + ``<Name>.names.txt``.
"""

from __future__ import annotations

import functools
import unicodedata
from dataclasses import dataclass
from importlib import resources
from pathlib import Path

from glyphsLib.glyphdata import get_glyph

PROJECT_GLYPHSET_DIR: Path | None = None

DATA = resources.files("octalfont") / "data" / "glyphsets"


@dataclass(frozen=True)
class GlyphInfo:
    name: str
    unicode: int | None
    category: str | None
    subcategory: str | None

    @property
    def is_nonspacing_mark(self) -> bool:
        return self.category == "Mark" and self.subcategory == "Nonspacing"

    @property
    def is_letter(self) -> bool:
        return self.category == "Letter"


@functools.lru_cache(maxsize=None)
def glyph_info(name: str) -> GlyphInfo:
    """Resolve a nice glyph name to its Unicode value and category."""

    g = get_glyph(name)
    uni = int(g.unicode, 16) if g.unicode else None

    return GlyphInfo(name, uni, g.category, g.subCategory)


def _read(name: str, suffix: str) -> str:
    if PROJECT_GLYPHSET_DIR is not None:
        local = PROJECT_GLYPHSET_DIR / f"{name}{suffix}"

        if local.is_file():
            return local.read_text(encoding="utf-8")

    ref = DATA / f"{name}{suffix}"

    if not ref.is_file():
        raise KeyError(f"unknown glyph set '{name}' (no {name}{suffix})")

    return ref.read_text(encoding="utf-8")


@functools.lru_cache(maxsize=None)
def glyphset_unicodes(glyphset: str) -> list[int]:
    """Codepoints of a glyph set (e.g. ``GF_Latin_Core``)."""
    out = []

    for line in _read(glyphset, ".nam").splitlines():
        line = line.split("#", 1)[0].strip()

        if line.startswith("0x"):
            out.append(int(line, 16))

    return sorted(out)


@functools.lru_cache(maxsize=None)
def _nice_names(glyphset: str) -> tuple[str, ...]:
    lines = _read(glyphset, ".names.txt").splitlines()
    return tuple(ln.strip() for ln in lines if ln.strip() and not ln.startswith("#"))


@functools.lru_cache(maxsize=None)
def nice_name_map(*glyphset_names: str) -> dict[int, str]:
    """codepoint -> GF nice name for the given glyphsets."""

    out: dict[int, str] = {}

    for gs in glyphset_names:
        for name in _nice_names(gs):
            uni = glyph_info(name).unicode

            if uni is not None:
                out.setdefault(uni, name)

    return out


def glyph_name_for(codepoint: int, *glyphset_names: str) -> str:
    """Nice name for a codepoint, falling back to ``uniXXXX``."""
    return nice_name_map(*glyphset_names).get(codepoint) or f"uni{codepoint:04X}"


def decompose(codepoint: int) -> list[int] | None:
    """Canonical (NFD) decomposition, or None if the character is atomic."""

    parts = unicodedata.normalize("NFD", chr(codepoint))

    if len(parts) < 2:
        return None

    return [ord(c) for c in parts]
