import ufoLib2

from octalfont.composites import CompositeConfig, build_composites, place_marks


def _font():
    f = ufoLib2.Font()

    for name, cp, box in [("A", 0x41, (0, 0, 700, 700)), ("acutecomb", 0x301, (-100, 400, 100, 700))]:
        g = f.newGlyph(name)
        g.unicodes = [cp]
        g.width = 0 if name.endswith("comb") else 850
        pen = g.getPen()
        x0, y0, x1, y1 = box

        pen.moveTo((x0, y0))
        pen.lineTo((x1, y0))
        pen.lineTo((x1, y1))
        pen.lineTo((x0, y1))
        pen.closePath()

    return f


def test_mark_sits_above_with_gap():
    f = _font()
    cfg = CompositeConfig(gap=40)
    (p,) = place_marks(f, cfg, "Aacute", "A", [("acutecomb", 0x301)])

    assert p.dy == 700 + 40 - 400 and p.dx == 350


def test_override_moves_mark():
    f = _font()
    cfg = CompositeConfig(gap=40, overrides={"Aacute": {"acutecomb": {"dx": 25, "dy": -10}}})
    (p,) = place_marks(f, cfg, "Aacute", "A", [("acutecomb", 0x301)])

    assert p.dx == 375 and p.dy == 330


def test_unicode_composite_built_and_drawn_glyph_kept():
    f = _font()
    rep = build_composites(f, CompositeConfig(), [0xC1], ["GF_Latin_Core"])

    assert "Aacute" in rep["built"] and f["Aacute"].width == 850
