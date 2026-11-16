"""Composite glyph engine: base letter + combining marks, with tunable placement.

Precomposed letters (``Aacute``, ``Ccedilla``, ``Ắ`` ...) are derived from the
Unicode decomposition of every character in the target glyph sets. Marks are
attached by their bounding boxes (no hand-kept anchor tables), and every
number can be overridden in ``composites.yaml``:

    gap: 40            # default space between base and first mark
    stack_gap: 20      # space between stacked marks
    marks:             # per-mark defaults (by glyph name)
      cedillacomb: {gap: 0}
    overrides:         # per resulting glyph, per mark
      Aacute: {acutecomb: {dx: 10, dy: -5}}
    anchors:           # explicit base anchors for odd shapes
      J: {top: [310, 700]}
    exclude: [Ldot]    # never auto-build these
    glyphs:            # manual recipes (non-Unicode-derivable)
      dcaron: {base: d, marks: [caroncomb]}

Anchors (``top``/``bottom`` on bases, ``_top``/``_bottom`` on marks) are also
written into the UFO so ufo2ft generates ``mark``/``mkmk`` GPOS for sequences
that have no precomposed glyph.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import ufoLib2
import yaml
from ufoLib2.objects import Component

from .glyphnames import decompose, glyph_info, glyph_name_for

ABOVE_CCC = {230, 232, 228, 234}
BELOW_CCC = {202, 220, 233, 218, 222, 224}
# Latin letters whose dot must disappear when a mark sits above them
SOFT_DOTTED = {"i": "dotlessi", "j": "uni0237"}


@dataclass
class CompositeConfig:
    gap: float = 40
    stack_gap: float = 20
    auto: bool = True
    marks: dict[str, dict[str, Any]] = field(default_factory=dict)
    overrides: dict[str, dict[str, dict[str, float]]] = field(default_factory=dict)
    anchors: dict[str, dict[str, list[float]]] = field(default_factory=dict)
    exclude: set[str] = field(default_factory=set)
    glyphs: dict[str, dict[str, Any]] = field(default_factory=dict)

    @classmethod
    def load(cls, path: Path) -> "CompositeConfig":
        if not path.is_file():
            return cls()

        d = yaml.safe_load(path.read_text(encoding="utf-8")) or {}

        return cls(
            gap=d.get("gap", 40),
            stack_gap=d.get("stack_gap", 20),
            auto=d.get("auto", True),
            marks=d.get("marks", {}) or {},
            overrides=d.get("overrides", {}) or {},
            anchors=d.get("anchors", {}) or {},
            exclude=set(d.get("exclude", []) or []),
            glyphs=d.get("glyphs", {}) or {},
        )


@dataclass
class Placement:
    mark: str
    dx: float
    dy: float
    side: str  # "above" | "below"


def _bounds(font: ufoLib2.Font, name: str):
    return font[name].getBounds(font.layers.defaultLayer)


def _side(codepoint: int) -> str:
    ccc = unicodedata.combining(chr(codepoint))

    return "below" if ccc in BELOW_CCC else "above"


def place_marks(
    font: ufoLib2.Font,
    cfg: CompositeConfig,
    target: str,
    base: str,
    marks: list[tuple[str, int]],
) -> list[Placement] | None:
    """Compute component offsets for ``marks`` stacked on ``base``.

    ``marks`` is ``[(mark_glyph_name, mark_codepoint), ...]``. Returns None
    when the base or a mark has no outline to measure.
    """

    bb = _bounds(font, base)

    if bb is None:
        return None

    manual = cfg.anchors.get(base, {})
    cx = (bb[0] + bb[2]) / 2
    top_y, bottom_y = bb[3], bb[1]

    if "top" in manual:
        cx, top_y = manual["top"]

    if "bottom" in manual:
        bottom_y = manual["bottom"][1]

    ov_glyph = cfg.overrides.get(target, {})
    out: list[Placement] = []
    n_above = n_below = 0

    for mark, cp in marks:
        mb = _bounds(font, mark)

        if mb is None:
            return None

        defaults = cfg.marks.get(mark, {})
        ov = ov_glyph.get(mark, {})
        side = defaults.get("side") or _side(cp)
        mcx = (mb[0] + mb[2]) / 2

        if defaults.get("anchor_x") == "right":
            ax = bb[2] - (mb[2] - mb[0]) / 2
        elif defaults.get("anchor_x") == "left":
            ax = bb[0] + (mb[2] - mb[0]) / 2
        else:
            ax = cx

        first = (n_above if side == "above" else n_below) == 0
        gap = ov.get("gap", defaults.get("gap", cfg.gap if first else cfg.stack_gap))

        if side == "above":
            dy = top_y + gap - mb[1]
            top_y = mb[3] + dy + ov.get("dy", 0)
            n_above += 1
        else:
            dy = bottom_y - gap - mb[3]
            bottom_y = mb[1] + dy + ov.get("dy", 0)
            n_below += 1

        out.append(Placement(mark, round(ax - mcx + ov.get("dx", 0)),
                             round(dy + ov.get("dy", 0)), side))

    return out


def estimate_stack_top(font: ufoLib2.Font, cfg: CompositeConfig, base: str,
                       codepoints: list[int]) -> float | None:
    """Highest point of ``base`` + marks without creating a glyph."""

    cmap = _cmap(font)
    marks = []

    for cp in codepoints:
        name = cmap.get(cp)

        if name is None:
            return None

        marks.append((name, cp))

    placed = place_marks(font, cfg, "__estimate__", base, marks)

    if placed is None:
        return None

    top = _bounds(font, base)[3]

    for p in placed:
        mb = _bounds(font, p.mark)
        top = max(top, mb[3] + p.dy)

    return top


def _cmap(font: ufoLib2.Font) -> dict[int, str | None]:
    return {u: g.name for g in font for u in g.unicodes}


def _add_composite(font, name, cp, base, placements) -> None:
    g = font.newGlyph(name)

    if cp is not None:
        g.unicodes = [cp]

    g.width = font[base].width

    g.components.append(Component(baseGlyph=base))

    for p in placements:
        g.components.append(Component(baseGlyph=p.mark, transformation=(1, 0, 0, 1, p.dx, p.dy)))


def build_composites(font: ufoLib2.Font, cfg: CompositeConfig,
                     targets: list[int], glyphsets: list[str]) -> dict[str, list[str]]:
    """Create composite glyphs; returns a report ``{built, skipped, missing}``."""
    report: dict[str, list[str]] = {"built": [], "skipped_drawn": [], "missing_parts": []}
    cmap = _cmap(font)

    # 1) manual recipes
    for name, recipe in cfg.glyphs.items():
        if name in font:
            report["skipped_drawn"].append(name)
            continue

        base = recipe["base"]
        mark_names = recipe.get("marks", [])
        marks = [(m, next(iter(font[m].unicodes), 0x0301)) for m in mark_names if m in font]

        if base not in font or len(marks) != len(mark_names):
            report["missing_parts"].append(name)
            continue

        placed = place_marks(font, cfg, name, base, marks)

        if placed is None:
            report["missing_parts"].append(name)
            continue

        info = glyph_info(name)

        _add_composite(font, name, info.unicode, base, placed)
        report["built"].append(name)

    if not cfg.auto:
        return report

    # 2) Unicode-derived composites
    for cp in targets:
        parts = decompose(cp)

        if parts is None:
            continue

        name = glyph_name_for(cp, *glyphsets)

        if name in cfg.exclude:
            continue

        if name in font or cp in cmap:
            report["skipped_drawn"].append(name)
            continue

        base_cp, mark_cps = parts[0], parts[1:]

        if not all(unicodedata.combining(chr(m)) for m in mark_cps):
            continue

        base_name = cmap.get(base_cp)

        if base_name is None:
            report["missing_parts"].append(name)
            continue

        if chr(base_cp) in SOFT_DOTTED and any(_side(m) == "above" for m in mark_cps):
            alt = cmap.get(ord(SOFT_DOTTED[chr(base_cp)] if len(SOFT_DOTTED[chr(base_cp)]) == 1 else "\0"))
            alt = alt or next((g.name for g in font if g.name == SOFT_DOTTED[chr(base_cp)]), None)
            base_name = alt or base_name

        marks = []

        for m in mark_cps:
            mname = cmap.get(m)

            if mname is None:
                break

            marks.append((mname, m))

        if len(marks) != len(mark_cps):
            report["missing_parts"].append(name)
            continue

        placed = place_marks(font, cfg, name, base_name, marks)

        if placed is None:
            report["missing_parts"].append(name)
            continue

        _add_composite(font, name, cp, base_name, placed)
        report["built"].append(name)

    return report


def write_anchors(font: ufoLib2.Font, cfg: CompositeConfig) -> None:
    """Add ``top``/``bottom`` to letters and ``_top``/``_bottom`` (+stack) to marks."""

    for g in font:
        if g.components:
            continue

        name = g.name

        if name is None:
            continue

        info = glyph_info(name)
        bb = g.getBounds(font.layers.defaultLayer)

        if bb is None:
            continue

        g.anchors = [a for a in g.anchors if a.name not in {"top", "bottom", "_top", "_bottom"}]
        cx = (bb[0] + bb[2]) / 2

        if info.is_nonspacing_mark and info.unicode is not None:
            defaults = cfg.marks.get(name, {})
            side = defaults.get("side") or _side(info.unicode)

            if side == "above":
                g.appendAnchor({"name": "_top", "x": round(cx), "y": round(bb[1])})
                g.appendAnchor({"name": "top", "x": round(cx), "y": round(bb[3] + cfg.stack_gap)})
            else:
                g.appendAnchor({"name": "_bottom", "x": round(cx), "y": round(bb[3])})
                g.appendAnchor({"name": "bottom", "x": round(cx), "y": round(bb[1] - cfg.stack_gap)})
        elif info.is_letter:
            manual = cfg.anchors.get(name, {})
            tx, ty = manual.get("top", (cx, bb[3] + cfg.gap))
            bx, by = manual.get("bottom", (cx, bb[1] - cfg.gap))

            g.appendAnchor({"name": "top", "x": round(tx), "y": round(ty)})
            g.appendAnchor({"name": "bottom", "x": round(bx), "y": round(by)})
