"""SVG-to-font-unit coordinate transform.

Coordinate mapping (Y-down SVG to Y-up font):
    scale  = cap_height / svg_ref_size
    x_font = x_svg * scale
    y_font = cap_height - y_svg * scale
"""

from __future__ import annotations


class Transform:
    """Convert SVG artboard coordinates to UFO font units.

    The artboard is assumed to be a square of side svg_ref (default 1000).
    Y = 0 sits at the top of capitals; Y = svg_ref sits at the baseline.
    Descenders have Y > svg_ref.
    """

    def __init__(self, cap_height: float, svg_ref: float) -> None:
        """Initialize the transform.

        Args:
            cap_height: Cap-height in font units, e.g. 700.
            svg_ref: SVG artboard side length, e.g. 1000.
        """

        self.scale: float = cap_height / svg_ref
        self.cap_height: float = cap_height

    def pt(self, svg_x: float, svg_y: float) -> tuple[float, float]:
        """Convert a single SVG point to font units.

        Args:
            svg_x: X coordinate in SVG space.
            svg_y: Y coordinate in SVG space.

        Returns:
            A tuple (x_font, y_font) rounded to 3 decimal places.
        """

        return (
            round(svg_x * self.scale, 3),
            round(self.cap_height - svg_y * self.scale, 3),
        )
