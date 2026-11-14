"""Build master UFOs from SVG glyph sources and a FontConfig."""

from __future__ import annotations

from pathlib import Path

import ufoLib2
from fontTools.misc.transform import Transform
from fontTools.pens.recordingPen import RecordingPen
from fontTools.pens.transformPen import TransformPen

from .composites import CompositeConfig, build_composites, write_anchors
from .config import OFL_LICENSE, OFL_URL, FontConfig, Master
from .glyphnames import glyph_info, glyphset_unicodes
from .svg import draw_svg


def _set_info(ufo: ufoLib2.Font, cfg: FontConfig, master: Master) -> None:
    i, m = ufo.info, cfg.metrics
    regular_like = master.weight in (400, 700)
    i.familyName = cfg.family
    i.styleName = master.style
    i.styleMapFamilyName = cfg.family if regular_like else f"{cfg.family} {master.style}"
    i.styleMapStyleName = "bold" if master.weight == 700 else "regular"
    i.postscriptFontName = cfg.ps_name(master.style)
    major, minor = cfg.version_major_minor
    i.versionMajor, i.versionMinor = major, minor
    i.copyright = cfg.copyright
    i.openTypeNameLicense = OFL_LICENSE
    i.openTypeNameLicenseURL = OFL_URL
    i.openTypeNameDesigner = cfg.designer
    i.openTypeNameDesignerURL = cfg.designer_url
    i.openTypeNameManufacturer = cfg.manufacturer
    i.openTypeNameManufacturerURL = cfg.manufacturer_url
    i.openTypeNameDescription = cfg.description
    i.openTypeOS2VendorID = cfg.vendor_id
    i.openTypeOS2WeightClass = master.weight
    i.openTypeOS2Type = []
    i.openTypeOS2Selection = [7]  # USE_TYPO_METRICS
    i.unitsPerEm = m.upm
    i.capHeight, i.xHeight = m.cap_height, m.x_height
    i.ascender, i.descender = m.ascender, m.descender
    i.openTypeHheaAscender = i.openTypeOS2TypoAscender = m.ascender
    i.openTypeHheaDescender = i.openTypeOS2TypoDescender = m.descender
    i.openTypeHheaLineGap = i.openTypeOS2TypoLineGap = 0
    i.postscriptUnderlinePosition = m.underline_position
    i.postscriptUnderlineThickness = m.underline_thickness

    if cfg.spacing.mode == "monospace":
        i.postscriptIsFixedPitch = True
        i.openTypeOS2Panose = [2, 0, 0, 9, 0, 0, 0, 0, 0, 0]  # bProportion = monospaced


def import_svgs(ufo: ufoLib2.Font, cfg: FontConfig, svg_dir: Path) -> list[str]:
    """Import every ``*.svg`` under ``svg_dir`` (file stem = GF nice glyph name)."""

    s, sp = cfg.metrics.cap_height / cfg.svg.artboard, cfg.spacing
    to_font = Transform(s, 0, 0, -s, 0, cfg.metrics.cap_height)  # y=0 -> cap height
    warnings: list[str] = []

    for svg in sorted(svg_dir.rglob("*.svg")):
        name = svg.stem
        info = glyph_info(name)

        if info.unicode is None and info.category is None and name != ".notdef":
            warnings.append(f"{svg.name}: unknown glyph name '{name}' (kept unencoded)")

        g = ufo.newGlyph(name)

        if info.unicode is not None:
            g.unicodes = [info.unicode]

        rec = RecordingPen()
        vb_w = draw_svg(svg, rec, to_font)
        body = vb_w * s

        if sp.mode == "monospace":
            adv = sp.advance
            dx = (adv - body) / 2
        else:
            adv = round(body + sp.lsb + sp.rsb)
            dx = sp.lsb

        if info.is_nonspacing_mark and sp.zero_width_marks:
            dx -= adv / 2
            adv = 0

        rec.replay(TransformPen(g.getPen(), (1, 0, 0, 1, round(dx, 3), 0)))
        g.width = round(adv)

        for c in g.contours:
            for pt in c.points:
                pt.x, pt.y = round(pt.x, 3), round(pt.y, 3)

    return warnings


def _glyph_order(ufo: ufoLib2.Font) -> list[str | None]:
    def key(g):
        u = min(g.unicodes) if g.unicodes else 1 << 30

        return g.name != ".notdef", u, g.name

    return [g.name for g in sorted(ufo, key=key)]


def _production_names(ufo: ufoLib2.Font) -> dict[str, str]:
    """Nice name -> production (AGL / uniXXXX) name; compiled fonts must use the latter."""
    from glyphsLib.glyphdata import get_glyph

    out = {}

    for g in ufo:
        prod = get_glyph(g.name).production_name

        if prod and prod != g.name:
            out[g.name] = prod

    return out


def ensure_notdef(ufo: ufoLib2.Font, cfg: FontConfig) -> bool:
    """Draw a framed-box ``.notdef`` when none (or an empty one) was supplied."""

    if ".notdef" in ufo and len(ufo[".notdef"].contours) > 0:
        return False

    g = ufo[".notdef"] if ".notdef" in ufo else ufo.newGlyph(".notdef")
    adv = cfg.spacing.advance if cfg.spacing.mode == "monospace" else 600
    g.width = adv
    x0, x1, y1, w = adv * 0.1, adv * 0.9, cfg.metrics.cap_height, cfg.metrics.cap_height / 7
    pen = g.getPen()

    for (a, b, c, d), cw in [((x0, 0, x1, y1), False), ((x0 + w, w, x1 - w, y1 - w), True)]:
        pts = [(a, b), (c, b), (c, d), (a, d)]

        pen.moveTo(pts[0])

        for q in (reversed(pts[1:]) if cw else pts[1:]):
            pen.lineTo(q)

        pen.closePath()

    return True


def _categories(ufo: ufoLib2.Font) -> dict[str, str]:
    out = {}

    for g in ufo:
        info = glyph_info(g.name)
        out[g.name] = "mark" if info.is_nonspacing_mark else "base"

    return out


def build_master(cfg: FontConfig, master: Master, comp: CompositeConfig):
    ufo = ufoLib2.Font()
    _set_info(ufo, cfg, master)
    warnings = import_svgs(ufo, cfg, cfg.sources / master.svg)

    if ensure_notdef(ufo, cfg):
        warnings.append(".notdef was empty or missing; generated a default box (draw sources/svg/.../.notdef.svg to replace)")

    glyphsets = cfg.required_glyphsets + cfg.optional_glyphsets
    targets = sorted({u for gs in glyphsets for u in glyphset_unicodes(gs)})
    report = build_composites(ufo, comp, targets, glyphsets)

    write_anchors(ufo, comp)

    ufo.lib["public.glyphOrder"] = _glyph_order(ufo)
    ufo.lib["public.openTypeCategories"] = _categories(ufo)
    ufo.lib["public.postscriptNames"] = _production_names(ufo)
    ufo.lib["com.github.googlei18n.ufo2ft.useProductionNames"] = True
    fea = cfg.sources / cfg.features_file
    ufo.features.text = fea.read_text(encoding="utf-8") if fea.is_file() else (
        "languagesystem DFLT dflt;\nlanguagesystem latn dflt;\n"
    )

    return ufo, report, warnings


def font_extremes(ufos) -> tuple[int, int]:
    """Family-wide (yMax, yMin) over every glyph of every master (GF win metrics)."""

    ymax, ymin = 0.0, 0.0

    for ufo in ufos:
        layer = ufo.layers.defaultLayer

        for g in ufo:
            bb = g.getBounds(layer)

            if bb:
                ymin, ymax = min(ymin, bb[1]), max(ymax, bb[3])

    return round(ymax), round(ymin)
