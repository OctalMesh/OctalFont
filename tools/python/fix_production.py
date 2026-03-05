#!/usr/bin/env python3
"""
fix_production.py - Post-build fixups that gftools-fix-font doesn't apply.

Handles:
  - OS/2 fsSelection bit 7 (USE_TYPO_METRICS) - tells renderers to use
    sTypoAscender / sTypoDescender for line-box sizing instead of
    usWinAscent / usWinDescent.  Required by Google Fonts.
  - usWinAscent / usWinDescent recomputed from the real glyph bounding box.
  - meta table with dlng / slng script tags (googlefonts/meta check).

Usage:
  python tools/python/fix_production.py fonts/OctalFont-Titan/ttf/*.ttf
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

try:
    from fontTools.ttLib import TTFont, newTable
    from fontTools.pens.boundsPen import BoundsPen
except ImportError:
    raise SystemExit("[fix_production] fonttools not found. Run: octalfont env --setup")


# OS/2 fsSelection bit 7 - instructs renderers to prefer sTypo* line metrics.
# Without it Windows falls back to usWinAscent/Descent, breaking leading.
# https://learn.microsoft.com/typography/opentype/spec/os2#fsselection
_USE_TYPO_METRICS = 0x80


def _recompute_win_metrics(font: Any, path: Path) -> bool:
    """Recompute usWinAscent / usWinDescent from the actual compiled glyph outlines.

    Fontmake may seed these from UFO info values that predate the real extents;
    this pass ensures they always reflect what is actually in the binary.

    Args:
        font: Loaded TTFont object to inspect and modify.
        path: Path to the font file, used only for log output.

    Returns:
        True when the OS/2 table was modified.
    """

    glyph_set = font.getGlyphSet()
    global_ymax, global_ymin = 0, 0

    for glyph_name in glyph_set.keys():
        bounds_pen = BoundsPen(glyph_set)

        # noinspection PyBroadException
        # fontTools may raise any error for malformed glyphs.
        try:
            glyph_set[glyph_name].draw(bounds_pen)
        except Exception:
            continue

        if bounds_pen.bounds:
            _, ymin, _, ymax = bounds_pen.bounds
            global_ymax = max(global_ymax, ymax)
            global_ymin = min(global_ymin, ymin)

    new_ascent = max(global_ymax, 0)
    new_descent = max(-global_ymin, 0)
    os2_table: Any = font["OS/2"]

    if os2_table.usWinAscent == new_ascent and os2_table.usWinDescent == new_descent:
        return False

    os2_table.usWinAscent = new_ascent
    os2_table.usWinDescent = new_descent

    print(f"  [fix] WIN METRICS: ascent={new_ascent} descent={new_descent}  {path.name}")

    return True


def _add_meta_table(font: Any, path: Path) -> bool:
    """Add a meta table declaring Latin script support if one does not exist yet.

    Required by the googlefonts/meta/script_lang_tags fontbakery check.
    Values are Unicode ISO 15924 script tags.

    Args:
        font: Loaded TTFont object to modify.
        path: Path to the font file, used only for log output.

    Returns:
        True when the table was added.
    """

    if "meta" in font:
        return False

    meta_table: Any = newTable("meta")
    meta_table.data = {"dlng": "Latn", "slng": "Latn"}
    font["meta"] = meta_table

    print(f"  [fix] ADD meta table  {path.name}")

    return True


def fix_font(path: Path) -> bool:
    """Apply all production fixups to a single TTF/OTF file.

    Saves the file in-place only when at least one fix was applied.

    Args:
        path: Path to the font file to fix.

    Returns:
        True when the file was modified.
    """

    font: Any = TTFont(str(path))
    modified = False
    os2_table: Any = font["OS/2"]

    # USE_TYPO_METRICS (bit 7 of fsSelection)
    if not (os2_table.fsSelection & _USE_TYPO_METRICS):
        os2_table.fsSelection |= _USE_TYPO_METRICS
        modified = True
        print(f"  [fix] SET USE_TYPO_METRICS  {path.name}")

    if _recompute_win_metrics(font, path):
        modified = True

    if _add_meta_table(font, path):
        modified = True

    if modified:
        font.save(str(path))

    return modified


def main() -> int:
    """Run fix_production on all font paths given on the command line.

    Returns:
        0 on success, non-zero when one or more files failed.
    """

    if len(sys.argv) < 2:
        print("Usage: fix_production.py <font.ttf> [font2.ttf ...]")
        return 1

    paths = [Path(raw) for raw in sys.argv[1:]]
    errors = 0

    for font_path in paths:
        if not font_path.is_file():
            print(f"  [WARN] Not a file: {font_path}", file=sys.stderr)
            continue

        try:
            fix_font(font_path)
        except OSError as exc:
            print(f"  [ERROR] {font_path.name}: {exc}", file=sys.stderr)
            errors += 1

    return errors


if __name__ == "__main__":
    sys.exit(main())
