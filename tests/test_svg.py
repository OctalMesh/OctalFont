from fontTools.misc.transform import Transform
from fontTools.pens.boundsPen import BoundsPen

from octalfont.svg import draw_svg, parse_transform


def _bounds(tmp_path, body, viewbox="0 0 1000 1000"):
    f = tmp_path / "g.svg"
    f.write_text(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{viewbox}">{body}</svg>')

    pen = BoundsPen(None)
    width = draw_svg(f, pen, Transform())

    return pen.bounds, width


def test_rect_is_drawn(tmp_path):
    b, w = _bounds(tmp_path, '<rect x="100" y="200" width="300" height="50"/>')
    assert b == (100, 200, 400, 250) and w == 1000


def test_rotated_rect(tmp_path):
    b, _ = _bounds(tmp_path, '<rect x="0" y="0" width="400" height="200" transform="rotate(90)"/>')
    assert [round(v) for v in b] == [-200, 0, 0, 400]


def test_polygon_and_group_transform(tmp_path):
    b, _ = _bounds(tmp_path, '<g transform="translate(10 20)"><polygon points="0,0 100,0 100,50"/></g>')
    assert b == (10, 20, 110, 70)


def test_transform_parsing():
    t = parse_transform("translate(5 6) scale(2)")
    assert t.transformPoint((1, 1)) == (7, 8)
