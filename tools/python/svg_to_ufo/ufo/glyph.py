"""Draw SVG paths into a ufoLib2 Glyph via its PointPen."""

from __future__ import annotations

from pathlib import Path

import ufoLib2
from fontTools.pens.pointPen import AbstractPointPen

from svg_to_ufo.svg.loader import load_svg_paths
from svg_to_ufo.svg.parser import SvgPathToSegments
from svg_to_ufo.svg.transform import Transform


# Sub-path point: (x, y, segmentType_or_None_for_off_curve).
_SubPt = tuple[float, float, str | None]


def _flush_contour(
    pen: AbstractPointPen,
    subpath_points: list[_SubPt],
    closed: bool,
    lsb: float,
) -> None:
    """Emit a collected sub-path to the PointPen.

    Args:
        pen: PointPen to write into.
        subpath_points: Ordered list of (x, y, segmentType) triples.
        closed: Whether the sub-path ends with a Z command.
        lsb: Left side-bearing shift applied to every X coordinate.
    """

    if not subpath_points:
        return

    pen.beginPath()

    for i, (point_x, point_y, segment_type) in enumerate(subpath_points):
        if i == 0 and not closed:
            pen.addPoint((point_x + lsb, point_y), segmentType="move")
        else:
            pen.addPoint((point_x + lsb, point_y), segmentType=segment_type)

    pen.endPath()


def svg_to_glyph(
    svg_path: Path,
    glyph: ufoLib2.objects.Glyph,
    transform: Transform,
    advance_width: float | None = None,
    lsb: int = 0,
    rsb: int = 0,
) -> None:
    """Parse svg_path and draw its contours into glyph.

    The advance width is computed as body_width + lsb + rsb where
    body_width is derived from the SVG viewBox. Pass advance_width to
    override this calculation (e.g. for a fixed-width font). Contour
    points are shifted right by lsb, placing the outline within bearings.

    Args:
        svg_path: Path to the source .svg file.
        glyph: ufoLib2 Glyph object to draw into.
        transform: Coordinate transform from SVG space to font units.
        advance_width: Override the computed advance width in font units.
        lsb: Left side-bearing in font units.
        rsb: Right side-bearing in font units.
    """

    viewbox_w, path_data = load_svg_paths(svg_path)
    pen = glyph.getPointPen()

    if advance_width is None:
        body_w = round(viewbox_w * transform.scale)
        glyph.width = body_w + lsb + rsb
    else:
        glyph.width = round(advance_width)

    for path_d_string in path_data:
        parser = SvgPathToSegments(path_d_string)

        subpath_points: list[_SubPt] = []
        start_point: tuple[float, float] = (0.0, 0.0)

        for segment_type, segment_points in parser.segments():
            if segment_type == "moveto":
                if subpath_points:
                    _flush_contour(pen, subpath_points, closed=False, lsb=lsb)

                font_x, font_y = transform.pt(*segment_points[0])
                start_point = (font_x, font_y)
                subpath_points = [(font_x, font_y, "line")]

            elif segment_type == "lineto":
                if not subpath_points:
                    continue

                font_x, font_y = transform.pt(*segment_points[0])
                subpath_points.append((font_x, font_y, "line"))

            elif segment_type == "curveto":
                if not subpath_points:
                    continue

                ctrl1_x, ctrl1_y = transform.pt(*segment_points[0])
                ctrl2_x, ctrl2_y = transform.pt(*segment_points[1])
                end_x, end_y = transform.pt(*segment_points[2])

                subpath_points.append((ctrl1_x, ctrl1_y, None))
                subpath_points.append((ctrl2_x, ctrl2_y, None))
                subpath_points.append((end_x, end_y, "curve"))

            elif segment_type == "qcurveto":
                if not subpath_points:
                    continue

                ctrl1_x, ctrl1_y = transform.pt(*segment_points[0])
                end_x, end_y = transform.pt(*segment_points[1])

                subpath_points.append((ctrl1_x, ctrl1_y, None))
                subpath_points.append((end_x, end_y, "qcurve"))

            elif segment_type == "closepath":
                if subpath_points:
                    last_point = subpath_points[-1]
                    start_x, start_y = start_point

                    if (
                        abs(last_point[0] - start_x) < 0.5
                        and abs(last_point[1] - start_y) < 0.5
                        and last_point[2] is not None
                    ):
                        subpath_points.pop()

                _flush_contour(pen, subpath_points, closed=True, lsb=lsb)
                subpath_points = []

        if subpath_points:
            _flush_contour(pen, subpath_points, closed=False, lsb=lsb)
