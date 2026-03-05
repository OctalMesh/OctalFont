"""SVG file reader and path extractor.

Handles <path>, <polygon>, and <polyline> elements.
"""

from __future__ import annotations

import re
from pathlib import Path
from xml.etree import ElementTree

from svg_to_ufo.config import SVG_NS


def _points_attr_to_path(points_str: str, *, close: bool) -> str:
    """Convert a <polygon>/<polyline> points attribute to a path d string.

    Args:
        points_str: Raw points attribute, whitespace/comma-separated pairs.
        close: True for <polygon> (appends Z), False for <polyline>.

    Returns:
        An SVG path d string, or an empty string for degenerate input.
    """

    raw_tokens = re.split(r"[\s,]+", points_str.strip())
    raw_tokens = [token for token in raw_tokens if token]

    if len(raw_tokens) < 4 or len(raw_tokens) % 2 != 0:
        return ""

    coordinates = [float(token) for token in raw_tokens]
    pairs = [(coordinates[i], coordinates[i + 1]) for i in range(0, len(coordinates), 2)]
    path_d = "M {},{}" .format(pairs[0][0], pairs[0][1])

    for pair_x, pair_y in pairs[1:]:
        path_d += " L {},{}" .format(pair_x, pair_y)

    if close:
        path_d += " Z"

    return path_d


def load_svg_paths(path: Path) -> tuple[float, list[str]]:
    """Parse an SVG file and extract all drawable path d strings.

    The viewBox width (or width attribute) is used downstream to compute
    the glyph advance width. Falls back to 1000 when neither is present.

    Args:
        path: Filesystem path to the .svg file.

    Returns:
        A tuple of (viewbox_width, list_of_d_strings).

    Raises:
        ValueError: When the root element is not <svg>.
    """

    tree = ElementTree.parse(path)
    root = tree.getroot()
    tag = root.tag.replace(f"{{{SVG_NS}}}", "")

    if tag != "svg":
        raise ValueError(f"Root element is not <svg>: {root.tag}")

    viewbox_w = 1000.0
    viewbox_attr = root.get("viewBox")

    if viewbox_attr:
        parts = viewbox_attr.split()

        if len(parts) == 4:
            viewbox_w = float(parts[2])
    elif root.get("width"):
        viewbox_w = float(root.get("width", "1000").rstrip("px"))

    path_strings: list[str] = []

    for elem in root.iter():
        local = elem.tag.replace(f"{{{SVG_NS}}}", "")

        if local == "path":
            path_d = elem.get("d", "").strip()

            if path_d:
                path_strings.append(path_d)

        elif local == "polygon":
            points_attr = elem.get("points", "").strip()

            if points_attr:
                path_d = _points_attr_to_path(points_attr, close=True)

                if path_d:
                    path_strings.append(path_d)

        elif local == "polyline":
            points_attr = elem.get("points", "").strip()

            if points_attr:
                # Glyph outlines are always closed filled shapes; close it
                # explicitly because Illustrator may export them open.
                path_d = _points_attr_to_path(points_attr, close=True)

                if path_d:
                    path_strings.append(path_d)

    return viewbox_w, path_strings
