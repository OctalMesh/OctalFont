"""SVG glyph outline reader.

Supports ``path``, ``rect``, ``polygon``, ``polyline``, ``circle`` and
``ellipse`` elements, nested ``<g>``, and the ``transform`` attribute
(``translate``, ``rotate``, ``scale``, ``matrix``, ``skewX/Y``).
"""

from __future__ import annotations

import re
from pathlib import Path
from xml.etree import ElementTree

from fontTools.misc.transform import Transform
from fontTools.pens.areaPen import AreaPen
from fontTools.pens.recordingPen import RecordingPen
from fontTools.pens.reverseContourPen import ReverseContourPen
from fontTools.pens.transformPen import TransformPen
from fontTools.svgLib.path import parse_path

SVG_NS = "{http://www.w3.org/2000/svg}"
_TRANSFORM_RE = re.compile(r"(\w+)\s*\(([^)]*)\)")
_NUM = re.compile(r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?")
_SKIP_TAGS = {"defs", "style", "title", "desc", "metadata", "clipPath", "mask"}


def _nums(text: str) -> list[float]:
    return [float(n) for n in _NUM.findall(text)]


def parse_transform(attr: str | None) -> Transform:
    """Parse an SVG ``transform`` attribute into a fontTools Transform."""
    t = Transform()

    for fn, args in _TRANSFORM_RE.findall(attr or ""):
        a = _nums(args)

        if fn == "translate":
            t = t.translate(a[0], a[1] if len(a) > 1 else 0)
        elif fn == "scale":
            t = t.scale(a[0], a[1] if len(a) > 1 else a[0])
        elif fn == "rotate":
            import math

            if len(a) == 3:
                t = t.translate(a[1], a[2]).rotate(math.radians(a[0])).translate(-a[1], -a[2])
            else:
                t = t.rotate(math.radians(a[0]))
        elif fn == "matrix":
            t = t.transform(tuple(a[:6]))
        elif fn == "skewX":
            import math

            t = t.skew(math.radians(a[0]), 0)
        elif fn == "skewY":
            import math

            t = t.skew(0, math.radians(a[0]))
        else:
            raise ValueError(f"unsupported SVG transform '{fn}'")

    return t


def _shape_path(tag: str, el: ElementTree.Element) -> str | None:
    """Return an SVG path ``d`` string for a basic shape element."""

    g = el.get

    if tag == "path":
        return g("d")

    if tag == "rect":
        x, y, w, h = (float(g(k, 0)) for k in ("x", "y", "width", "height"))
        return f"M{x},{y}H{x + w}V{y + h}H{x}Z"

    if tag in ("polygon", "polyline"):
        pts = _nums(g("points", ""))

        if len(pts) < 4:
            return None

        pairs = list(zip(pts[0::2], pts[1::2], strict=False))  # odd trailing value is ignored

        return "M" + "L".join(f"{x},{y}" for x, y in pairs) + "Z"

    if tag in ("circle", "ellipse"):
        cx, cy = float(g("cx", 0)), float(g("cy", 0))
        rx = float(g("r", g("rx", 0)))
        ry = float(g("r", g("ry", 0)))

        return (f"M{cx - rx},{cy}A{rx},{ry} 0 1 0 {cx + rx},{cy}"
                f"A{rx},{ry} 0 1 0 {cx - rx},{cy}Z")

    return None


def _contours(rec: RecordingPen) -> list[list]:
    out, cur = [], []

    for op, args in rec.value:
        cur.append((op, args))

        if op in ("closePath", "endPath"):
            out.append(cur)
            cur = []

    if cur:
        out.append(cur)

    return out


def _area(contour: list) -> float:
    rec = RecordingPen()
    rec.value = contour
    pen = AreaPen()

    rec.replay(pen)

    return pen.value


def _normalise(rec: RecordingPen) -> RecordingPen:
    """Make the element's outer contour counter-clockwise (positive area).

    Illustrator exports shapes with mixed winding. Without this, two
    overlapping elements of opposite winding would cancel into a hole under
    the non-zero fill rule once overlaps are removed.
    """

    contours = _contours(rec)

    if not contours:
        return rec

    outer = max(contours, key=lambda c: abs(_area(c)))

    if _area(outer) >= 0:
        return rec

    fixed = RecordingPen()

    for c in contours:
        tmp = RecordingPen()
        tmp.value = c

        tmp.replay(ReverseContourPen(fixed))

    return fixed


def draw_svg(path: Path, pen, transform: Transform) -> float:
    """Draw every filled shape of ``path`` into ``pen``.

    ``transform`` maps SVG space to font space (it should include the Y flip).
    Returns the SVG viewBox width (falls back to ``width`` or 1000).
    """

    root = ElementTree.parse(path).getroot()
    vb = root.get("viewBox")
    width = float(vb.split()[2]) if vb and len(vb.split()) == 4 else float(
        str(root.get("width", "1000")).rstrip("px")
    )

    def walk(el: ElementTree.Element, t: Transform) -> None:
        tag = el.tag.replace(SVG_NS, "")

        if tag in _SKIP_TAGS:
            return

        t = t.transform(parse_transform(el.get("transform"))) if el.get("transform") else t
        d = _shape_path(tag, el)

        if d:
            rec = RecordingPen()

            parse_path(d, TransformPen(rec, t))
            _normalise(rec).replay(pen)

        for child in el:
            walk(child, t)

    walk(root, transform)

    return width
