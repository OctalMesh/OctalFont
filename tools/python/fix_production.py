#!/usr/bin/env python3
"""
fix_production.py - Post-build fixups that gftools-fix-font doesn't apply.

Currently, handles:
  • OS/2 fsSelection bit 7 (USE_TYPO_METRICS) - tells renderers to use
    sTypoAscender / sTypoDescender for line-box sizing instead of
    usWinAscent / usWinDescent.  Required by Google Fonts.

Usage:
  python tools/python/fix_production.py fonts/OctalFont-Titan/ttf/*.ttf
"""

from __future__ import annotations

import sys
from pathlib import Path

try:
    from fontTools.ttLib import TTFont
    from fontTools.pens.boundsPen import BoundsPen
    from fontTools.ttLib.tables._m_e_t_a import table__m_e_t_a
except ImportError:
    sys.exit("[fix_production] fonttools not found. Run: octalfont env --setup")


def _recompute_win_metrics(tt: TTFont, path: Path) -> bool:
    """
    Set usWinAscent / usWinDescent to the actual compiled glyph bounding box.
    Fontmake may initialise these from UFO info values that predate the real
    glyph extents; this ensures they always match what's in the font.
    """
    glyph_set = tt.getGlyphSet()
    ymax_all, ymin_all = 0, 0
    for gname in glyph_set.keys():
        pen = BoundsPen(glyph_set)
        try:
            glyph_set[gname].draw(pen)
        except Exception:
            continue
        if pen.bounds:
            _, ymin, _, ymax = pen.bounds
            ymax_all = max(ymax_all, ymax)
            ymin_all = min(ymin_all, ymin)
    new_asc  = max(ymax_all, 0)
    new_desc = max(-ymin_all, 0)
    os2 = tt["OS/2"]
    if os2.usWinAscent == new_asc and os2.usWinDescent == new_desc:
        return False
    os2.usWinAscent  = new_asc
    os2.usWinDescent = new_desc
    print(f"  [fix] WIN METRICS: ascent={new_asc} descent={new_desc}  {path.name}")
    return True


def _add_meta_table(tt: TTFont, path: Path) -> bool:
    """
    Add a 'meta' table declaring Latin script support.
    Required by googlefonts/meta/script_lang_tags check.
    The values are Unicode script tags (ISO 15924).
    """
    if "meta" in tt:
        return False
    meta = table__m_e_t_a()
    meta.data = {"dlng": "Latn", "slng": "Latn"}
    tt["meta"] = meta
    print(f"  [fix] ADD meta table  {path.name}")
    return True


def fix_font(path: Path) -> bool:
    """Apply all production fixups to a single TTF/OTF file. Returns True if modified."""
    tt = TTFont(str(path))
    modified = False

    os2 = tt["OS/2"]

    # USE_TYPO_METRICS (bit 7 of fsSelection)
    # Without this bit, Windows uses usWinAscent/usWinDescent (which fontmake
    # sets to glyph-bbox max) for line spacing, causing inconsistent leading.
    # See: https://learn.microsoft.com/typography/opentype/spec/os2#fsselection
    USE_TYPO_METRICS = 0x80
    if not (os2.fsSelection & USE_TYPO_METRICS):
        os2.fsSelection |= USE_TYPO_METRICS
        modified = True
        print(f"  [fix] SET USE_TYPO_METRICS  {path.name}")

    if _recompute_win_metrics(tt, path):
        modified = True
    if _add_meta_table(tt, path):
        modified = True

    if modified:
        tt.save(str(path))

    return modified


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: fix_production.py <font.ttf> [font2.ttf ...]")
        return 1

    paths = [Path(p) for p in sys.argv[1:]]
    errors = 0

    for p in paths:
        if not p.is_file():
            print(f"  [WARN] Not a file: {p}", file=sys.stderr)
            continue
        try:
            fix_font(p)
        except Exception as exc:
            print(f"  [ERROR] {p.name}: {exc}", file=sys.stderr)
            errors += 1

    return errors


if __name__ == "__main__":
    sys.exit(main())
