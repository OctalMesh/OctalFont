"""Build a UFO master from per-glyph SVG files."""

from __future__ import annotations

import sys
from pathlib import Path

try:
    import ufoLib2
except ImportError:
    raise SystemExit("[svg_to_ufo] Missing dependency: ufoLib2\nRun: octalfont env --setup")

from svg_to_ufo.config import FEATURES_STUB
from svg_to_ufo.glyph_map import stem_to_glyph
from svg_to_ufo.svg.transform import Transform
from svg_to_ufo.ufo.glyph import svg_to_glyph


def build_ufo(
    family_dir: Path,
    weight_name: str,
    metrics: dict,
    dry_run: bool = False,
) -> Path:
    """Create a UFO master from the SVG files for a single weight.

    Looks for SVGs under ``<family_dir>/svg/<weight_name>/`` first, then
    falls back to a flat ``<family_dir>/svg/`` layout for legacy projects.
    The features.fea stub is only written on the first run; subsequent
    runs preserve the hand-edited file unchanged.

    Args:
        family_dir: Absolute path to the family source directory.
        weight_name: Weight to build, e.g. ``Regular`` or ``Bold``.
        metrics: Parsed metrics.yaml contents (see metrics.py).
        dry_run: When True, print what would happen without writing.

    Returns:
        The path to the UFO directory.

    Raises:
        FileNotFoundError: When no SVG files are found under the expected
            directory.
    """

    svg_root = (
        family_dir / "svg" / weight_name
        if (family_dir / "svg" / weight_name).is_dir()
        else family_dir / "svg"
    )
    ufo_path = family_dir / "ufo" / f"{weight_name}.ufo"

    # Extract metrics with safe defaults
    upm = int(metrics.get("upm", 1000))
    ascender = int(metrics.get("ascender", 800))
    descender = int(metrics.get("descender", -200))
    cap_height = int(metrics.get("cap_height", 700))
    x_height = int(metrics.get("x_height", 500))
    svg_ref = float(metrics.get("svg_ref_size", 1000))
    lsb = int(metrics.get("side_bearing_left", 0))
    rsb = int(metrics.get("side_bearing_right", 0))
    family_name_raw = metrics.get("family_name", family_dir.name)
    family_name = family_name_raw.replace("OctalFont-", "OctalFont ")

    transform = Transform(cap_height=cap_height, svg_ref=svg_ref)

    svg_files: list[Path] = sorted(svg_root.rglob("*.svg"))
    if not svg_files:
        raise FileNotFoundError(
            f"No SVG files found under {svg_root}\n"
            f"  Hint: add SVGs to svg/{weight_name}/ (per-weight) or svg/ (flat)"
        )

    print(f"  Found {len(svg_files)} SVG file(s) under {svg_root.relative_to(family_dir)}")

    if dry_run:
        for svg_file in svg_files:
            glyph_name, unicode_codepoint = stem_to_glyph(svg_file.stem)
            unicode_label = f" U+{unicode_codepoint:04X}" if unicode_codepoint else " (no unicode)"
            print(f"    {svg_file.relative_to(family_dir)}  ->  {glyph_name}{unicode_label}")

        return ufo_path

    # Build the UFO object
    ufo = ufoLib2.Font()

    # Basic font info
    ufo.info.familyName = family_name
    ufo.info.styleName = weight_name
    ufo.info.unitsPerEm = upm
    ufo.info.capHeight = cap_height
    ufo.info.xHeight = x_height
    ufo.info.postscriptUnderlinePosition = int(metrics.get("underline_position", -100))
    ufo.info.postscriptUnderlineThickness = int(metrics.get("underline_thickness", 50))

    # Version
    version_str = str(metrics.get("version", "1.000"))

    try:
        major_str, minor_str = version_str.split(".", 1)
        ufo.info.versionMajor = int(major_str)
        ufo.info.versionMinor = int(minor_str)
    except ValueError:
        ufo.info.versionMajor, ufo.info.versionMinor = 1, 0

    # Identity / legal name records.
    ufo.info.copyright = metrics.get("copyright", "")
    ufo.info.openTypeNameDesigner = metrics.get("designer", "")
    ufo.info.openTypeNameDesignerURL = metrics.get("designer_url", "")
    ufo.info.openTypeNameManufacturer = metrics.get("manufacturer", "")
    ufo.info.openTypeNameManufacturerURL = metrics.get("manufacturer_url", "")
    ufo.info.openTypeNameLicense = metrics.get("license", "")
    ufo.info.openTypeNameLicenseURL = metrics.get("license_url", "")
    ufo.info.openTypeOS2VendorID = str(metrics.get("vendor_id", "NONE"))[:4].upper()

    # fsType = 0 -> Installable Embedding (required for OFL / MIT fonts)
    # An empty list encodes value 0 in ufoLib2
    ufo.info.openTypeOS2Type = []

    # Vertical metrics
    # Google Fonts requires: hhea.ascender + |hhea.descender| + lineGap >= 1200
    # USE_TYPO_METRICS (fsSelection bit 7) is set by fix_production.py
    ufo.info.openTypeOS2TypoAscender = ascender
    ufo.info.openTypeOS2TypoDescender = descender
    ufo.info.openTypeOS2TypoLineGap = 0
    ufo.info.openTypeHheaAscender = ascender
    ufo.info.openTypeHheaDescender = descender
    ufo.info.openTypeHheaLineGap = 0
    # Win values are recomputed from the real glyph bounding box by
    # fix_production.py after compilation; set to a safe placeholder here
    ufo.info.openTypeOS2WinAscent = cap_height
    ufo.info.openTypeOS2WinDescent = 0
    ufo.info.ascender = ascender
    ufo.info.descender = descender

    # Add a .notdef glyph (empty rectangle as a fallback indicator)
    notdef = ufo.newGlyph(".notdef")
    notdef.width = round(cap_height * 0.6)
    notdef_pen = notdef.getPointPen()
    notdef_width = notdef.width
    notdef_height = cap_height
    notdef_margin = round(notdef_width * 0.1)
    notdef_stroke = round(notdef_width * 0.08)

    notdef_pen.beginPath()
    notdef_pen.addPoint((notdef_margin, 0), segmentType="line")
    notdef_pen.addPoint((notdef_width - notdef_margin, 0), segmentType="line")
    notdef_pen.addPoint((notdef_width - notdef_margin, notdef_height), segmentType="line")
    notdef_pen.addPoint((notdef_margin, notdef_height), segmentType="line")
    notdef_pen.endPath()
    notdef_pen.beginPath()
    notdef_pen.addPoint((notdef_margin + notdef_stroke, notdef_stroke), segmentType="line")
    notdef_pen.addPoint((notdef_margin + notdef_stroke, notdef_height - notdef_stroke), segmentType="line")
    notdef_pen.addPoint((notdef_width - notdef_margin - notdef_stroke, notdef_height - notdef_stroke), segmentType="line")
    notdef_pen.addPoint((notdef_width - notdef_margin - notdef_stroke, notdef_stroke), segmentType="line")
    notdef_pen.endPath()

    # Import SVG files
    skipped = imported = 0

    for svg_file in svg_files:
        glyph_name, unicode_codepoint = stem_to_glyph(svg_file.stem)

        try:
            glyph = ufo.newGlyph(glyph_name)

            if unicode_codepoint is not None:
                glyph.unicodes = [unicode_codepoint]

            svg_to_glyph(svg_file, glyph, transform, lsb=lsb, rsb=rsb)

            imported += 1
            unicode_label = f"U+{unicode_codepoint:04X}" if unicode_codepoint else "no-uni"

            print(
                f"    [{unicode_label}]  {glyph_name:20s}  <- {svg_file.relative_to(family_dir)}"
            )
        except Exception as exc:
            print(f"  [WARN] Skipping {svg_file.name}: {exc}", file=sys.stderr)
            skipped += 1

    print(f"  Imported: {imported}  |  Skipped: {skipped}")

    # Ensure the mandatory whitespace glyphs exist.
    if "space" not in ufo:
        space_glyph = ufo.newGlyph("space")
        space_glyph.unicodes = [0x0020]
        space_glyph.width = round(cap_height * 0.3)

    # U+00A0 NO-BREAK SPACE - required by fontbakery whitespace_glyphs check.
    if "nbspace" not in ufo:
        nbsp_glyph = ufo.newGlyph("nbspace")
        nbsp_glyph.unicodes = [0x00A0]
        nbsp_glyph.width = ufo["space"].width

    # Preserve the hand-edited features.fea when it already exists on disk.
    features_path = ufo_path / "features.fea"

    if features_path.exists():
        ufo.features.text = features_path.read_text(encoding="utf-8")
    else:
        ufo.features.text = FEATURES_STUB.format(family_name=family_name)

    ufo_path.parent.mkdir(parents=True, exist_ok=True)
    ufo.save(str(ufo_path), overwrite=True)
    print(f"  UFO written -> {ufo_path.relative_to(family_dir.parent.parent)}")

    return ufo_path
