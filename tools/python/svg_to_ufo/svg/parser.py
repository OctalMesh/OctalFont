"""SVG path d string tokenizer and segment generator.

Supported commands: M m L l H h V v C c S s Q q T t A a Z z

Arc commands are approximated with cubic Bezier segments (at most 4 per arc,
each spanning at most 90 degrees) following the SVG 1.1 spec conversion
algorithm defined in Appendix F.6.
"""

from __future__ import annotations

import math
import re
from collections.abc import Generator, Iterator

_PATH_TOKEN = re.compile(
    r"([MmLlHhVvCcSsQqTtAaZz])"
    r"|([+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)"
)

_NUMBER_RE = re.compile(
    r"^[+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?$"
)

def tokenize(d: str) -> Iterator[str]:
    """Yield individual tokens from an SVG path d attribute.

    Each token is either a single command letter or a numeric string.

    Args:
        d: Raw value of the SVG d attribute.

    Yields:
        Individual command letters or number strings.
    """
    for m in _PATH_TOKEN.finditer(d):
        yield m.group(0)


def _is_number(token: str) -> bool:
    return bool(_NUMBER_RE.fullmatch(token))


def arc_to_cubics(
    x1: float, y1: float,
    rx: float, ry: float,
    phi_deg: float,
    large_arc: int, sweep: int,
    x2: float, y2: float,
) -> list[tuple[float, float, float, float, float, float]]:
    """Convert one SVG arc to a list of cubic Bezier segments.

    Follows the endpoint-to-center parameterization from SVG 1.1 Appendix
    F.6. Splits arcs larger than 90 degrees into multiple segments to keep
    approximation error minimal.

    Args:
        x1: Start point X.
        y1: Start point Y.
        rx: X radius, scaled up when geometrically too small.
        ry: Y radius, scaled up when geometrically too small.
        phi_deg: X-axis rotation in degrees.
        large_arc: Large-arc flag (0 or 1).
        sweep: Sweep flag (0 or 1).
        x2: End point X.
        y2: End point Y.

    Returns:
        A list of (ctrl1_x, ctrl1_y, ctrl2_x, ctrl2_y, end_x, end_y) cubic segment tuples.
        Empty when start equals end.
    """

    if x1 == x2 and y1 == y2:
        return []

    if rx == 0 or ry == 0:
        return [(x1, y1, x2, y2, x2, y2)]

    phi_radians = math.radians(phi_deg)
    cos_phi = math.cos(phi_radians)
    sin_phi = math.sin(phi_radians)

    half_delta_x = (x1 - x2) / 2
    half_delta_y = (y1 - y2) / 2
    rotated_x1 =  cos_phi * half_delta_x + sin_phi * half_delta_y
    rotated_y1 = -sin_phi * half_delta_x + cos_phi * half_delta_y

    rx, ry = abs(rx), abs(ry)
    scale_factor = (rotated_x1 / rx) ** 2 + (rotated_y1 / ry) ** 2

    if scale_factor > 1:
        lam_sqrt = math.sqrt(scale_factor)
        rx *= lam_sqrt
        ry *= lam_sqrt

    sq_numerator = max(0.0, (rx * ry) ** 2 - (rx * rotated_y1) ** 2 - (ry * rotated_x1) ** 2)
    sq_denominator = (rx * rotated_y1) ** 2 + (ry * rotated_x1) ** 2
    center_scale = math.sqrt(sq_numerator / sq_denominator) if sq_denominator else 0.0

    if large_arc == sweep:
        center_scale = -center_scale

    center_prime_x =  center_scale * rx * rotated_y1 / ry
    center_prime_y = -center_scale * ry * rotated_x1 / rx
    arc_center_x = cos_phi * center_prime_x - sin_phi * center_prime_y + (x1 + x2) / 2
    arc_center_y = sin_phi * center_prime_x + cos_phi * center_prime_y + (y1 + y2) / 2

    def _angle(ux: float, uy: float, vx: float, vy: float) -> float:
        n = math.sqrt(ux * ux + uy * uy) * math.sqrt(vx * vx + vy * vy)

        if n == 0.0:
            return 0.0

        cos_a = max(-1.0, min(1.0, (ux * vx + uy * vy) / n))
        a = math.acos(cos_a)

        if ux * vy - uy * vx < 0:
            a = -a

        return a

    theta1 = _angle(1, 0, (rotated_x1 - center_prime_x) / rx, (rotated_y1 - center_prime_y) / ry)
    dtheta = _angle(
        (rotated_x1 - center_prime_x) / rx, (rotated_y1 - center_prime_y) / ry,
        (-rotated_x1 - center_prime_x) / rx, (-rotated_y1 - center_prime_y) / ry,
    )

    if not sweep and dtheta > 0:
        dtheta -= 2 * math.pi
    elif sweep and dtheta < 0:
        dtheta += 2 * math.pi

    # Split into at most 4 segments of <= 90 deg each.
    num_segments = max(1, math.ceil(abs(dtheta) / (math.pi / 2)))
    delta_theta = dtheta / num_segments
    bezier_alpha = math.sin(delta_theta) * (math.sqrt(4 + 3 * math.tan(delta_theta / 2) ** 2) - 1) / 3

    cubics: list[tuple[float, float, float, float, float, float]] = []
    current_theta = theta1

    for _ in range(num_segments):
        cos_theta_start = math.cos(current_theta)
        sin_theta_start = math.sin(current_theta)
        current_theta += delta_theta
        cos_theta_end = math.cos(current_theta)
        sin_theta_end = math.sin(current_theta)

        end_x = cos_phi * rx * cos_theta_end - sin_phi * ry * sin_theta_end + arc_center_x
        end_y = sin_phi * rx * cos_theta_end + cos_phi * ry * sin_theta_end + arc_center_y

        deriv_start_x = -rx * cos_phi * sin_theta_start - ry * sin_phi * cos_theta_start
        deriv_start_y = -rx * sin_phi * sin_theta_start + ry * cos_phi * cos_theta_start
        deriv_end_x   =  rx * cos_phi * sin_theta_end   + ry * sin_phi * cos_theta_end
        deriv_end_y   =  rx * sin_phi * sin_theta_end   - ry * cos_phi * cos_theta_end

        ctrl1_x = cos_phi * rx * cos_theta_start - sin_phi * ry * sin_theta_start + arc_center_x + bezier_alpha * deriv_start_x
        ctrl1_y = sin_phi * rx * cos_theta_start + cos_phi * ry * sin_theta_start + arc_center_y + bezier_alpha * deriv_start_y
        ctrl2_x = end_x - bezier_alpha * deriv_end_x
        ctrl2_y = end_y - bezier_alpha * deriv_end_y

        cubics.append((ctrl1_x, ctrl1_y, ctrl2_x, ctrl2_y, end_x, end_y))

    return cubics


# Segment type aliases used as the first element of each yielded tuple.
_SegType = str  # "moveto" | "lineto" | "curveto" | "qcurveto" | "closepath"
_Point = tuple[float, float]


class SvgPathToSegments:
    """Parse an SVG path d string and iterate over typed segments.

    Each segment is a (type, points) tuple. Points are (x, y) pairs in
    SVG coordinate space, before any font coordinate transform.

    Segment types and their point lists:
        ``moveto``    - [(x, y)]
        ``lineto``    - [(x, y)]
        ``curveto``   - [(c1x, c1y), (c2x, c2y), (x, y)]  cubic
        ``qcurveto``  - [(c1x, c1y), (x, y)]              quadratic
        ``closepath`` - []

    Typical usage::

        for seg_type, pts in SvgPathToSegments(d).segments():
            ...
    """

    def __init__(self, d: str) -> None:
        self._d = d

    def segments(self) -> Generator:
        """Yield (seg_type, points) tuples for every segment in the d string."""

        tokens = tokenize(self._d)
        command: str | None = None
        x = y = 0.0
        start_x = start_y = 0.0
        last_ctrl2_x = last_ctrl2_y = 0.0
        last_quad_x = last_quad_y = 0.0
        prev_command: str | None = None

        try:
            token = next(tokens)
        except StopIteration:
            return

        while True:
            if re.fullmatch(r"[MmLlHhVvCcSsQqTtAaZz]", token):
                command = token

                try:
                    token = next(tokens)
                except StopIteration:
                    token = ""

            if command is None:
                break

            def _read(count: int) -> list[float]:
                nonlocal token
                result: list[float] = []

                while len(result) < count:
                    if not _is_number(token):
                        raise ValueError(f"Expected number, got {token!r}")

                    result.append(float(token))

                    try:
                        token = next(tokens)
                    except StopIteration:
                        token = ""

                return result

            # ---- M / m ----
            if command in ("M", "m"):
                values = _read(2)
                if command == "m":
                    x += values[0]; y += values[1]
                else:
                    x, y = values[0], values[1]

                start_x, start_y = x, y

                yield "moveto", [(x, y)]

                command = "l" if command == "m" else "L"
                prev_command = "M"

                continue

            # ---- Z / z ----
            elif command in ("Z", "z"):
                yield "closepath", []
                x, y = start_x, start_y
                # Do NOT consume another token here; the stream already has
                # the next command/coordinate in `token`.

            # ---- L / l ----
            elif command in ("L", "l"):
                values = _read(2)

                if command == "l":
                    x += values[0]; y += values[1]
                else:
                    x, y = values[0], values[1]

                yield "lineto", [(x, y)]

            # ---- H / h ----
            elif command in ("H", "h"):
                values = _read(1)
                x = x + values[0] if command == "h" else values[0]

                yield "lineto", [(x, y)]

            # ---- V / v ----
            elif command in ("V", "v"):
                values = _read(1)
                y = y + values[0] if command == "v" else values[0]

                yield "lineto", [(x, y)]

            # ---- C / c ----
            elif command in ("C", "c"):
                values = _read(6)

                if command == "c":
                    ctrl1_x = x + values[0]; ctrl1_y = y + values[1]
                    ctrl2_x = x + values[2]; ctrl2_y = y + values[3]
                    end_x   = x + values[4]; end_y   = y + values[5]
                else:
                    ctrl1_x, ctrl1_y, ctrl2_x, ctrl2_y, end_x, end_y = values

                last_ctrl2_x, last_ctrl2_y = ctrl2_x, ctrl2_y
                x, y = end_x, end_y

                yield "curveto", [(ctrl1_x, ctrl1_y), (ctrl2_x, ctrl2_y), (x, y)]

            # ---- S / s  (smooth cubic) ----
            elif command in ("S", "s"):
                values = _read(4)

                if command == "s":
                    ctrl2_x = x + values[0]; ctrl2_y = y + values[1]
                    end_x   = x + values[2]; end_y   = y + values[3]
                else:
                    ctrl2_x, ctrl2_y, end_x, end_y = values

                ctrl1_x = 2 * x - last_ctrl2_x if prev_command in ("C", "c", "S", "s") else x
                ctrl1_y = 2 * y - last_ctrl2_y if prev_command in ("C", "c", "S", "s") else y
                last_ctrl2_x, last_ctrl2_y = ctrl2_x, ctrl2_y
                x, y = end_x, end_y

                yield "curveto", [(ctrl1_x, ctrl1_y), (ctrl2_x, ctrl2_y), (x, y)]

            # ---- Q / q  (quadratic) ----
            elif command in ("Q", "q"):
                values = _read(4)

                if command == "q":
                    ctrl1_x = x + values[0]; ctrl1_y = y + values[1]
                    end_x   = x + values[2]; end_y   = y + values[3]
                else:
                    ctrl1_x, ctrl1_y, end_x, end_y = values

                last_quad_x, last_quad_y = ctrl1_x, ctrl1_y
                x, y = end_x, end_y

                yield "qcurveto", [(ctrl1_x, ctrl1_y), (x, y)]

            # ---- T / t  (smooth quadratic) ----
            elif command in ("T", "t"):
                values = _read(2)

                if command == "t":
                    end_x = x + values[0]; end_y = y + values[1]
                else:
                    end_x, end_y = values

                ctrl1_x = 2 * x - last_quad_x if prev_command in ("Q", "q", "T", "t") else x
                ctrl1_y = 2 * y - last_quad_y if prev_command in ("Q", "q", "T", "t") else y
                last_quad_x, last_quad_y = ctrl1_x, ctrl1_y
                x, y = end_x, end_y

                yield "qcurveto", [(ctrl1_x, ctrl1_y), (x, y)]

            # ---- A / a  (arc -> cubic) ----
            elif command in ("A", "a"):
                values = _read(7)

                if command == "a":
                    arc_end_x = x + values[5]; arc_end_y = y + values[6]
                else:
                    arc_end_x, arc_end_y = values[5], values[6]

                arc_cubics = arc_to_cubics(
                    x, y,
                    values[0], values[1],
                    values[2],
                    int(values[3]), int(values[4]),
                    arc_end_x, arc_end_y,
                )

                for ctrl1_x, ctrl1_y, ctrl2_x, ctrl2_y, seg_end_x, seg_end_y in arc_cubics:
                    last_ctrl2_x, last_ctrl2_y = ctrl2_x, ctrl2_y

                    yield "curveto", [(ctrl1_x, ctrl1_y), (ctrl2_x, ctrl2_y), (seg_end_x, seg_end_y)]

                x, y = arc_end_x, arc_end_y

            else:
                # Unrecognised command - skip token and attempt to continue.
                try:
                    token = next(tokens)
                except StopIteration:
                    break

                prev_command = command
                continue

            prev_command = command

            if not token or not _is_number(token):
                if not token:
                    break
                # Next token is a command letter; stay in the outer loop.
