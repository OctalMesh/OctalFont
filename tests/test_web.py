from __future__ import annotations

import json
from pathlib import Path

import pytest
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont, newTable
from fontTools.ttLib.tables._f_v_a_r import Axis

from octalfont import web
from octalfont.config import load_config

FONT_YAML = """family: Demo Font
version: "1.012"
copyright_year: 2025
repository: https://github.com/Example/demo-font
vendor_id: DEMO
designer: Someone
designer_url: https://example.com
description: A demo.
glyphsets:
  required: [GF_Latin_Core]
  optional: [GF_Cyrillic_Plus]
scripts: [Latn, Cyrl]
"""
CODEPOINTS = {0x20: "space", 0x41: "A", 0x42: "B", 0x42F: "Ya-cy", 0x416: "Zhe-cy"}


def make_ttf(path: Path, weight: int = 400, italic: bool = False) -> None:
    order = [".notdef", *CODEPOINTS.values()]
    fb = FontBuilder(1000, isTTF=True)

    fb.setupGlyphOrder(order)
    fb.setupCharacterMap(dict(CODEPOINTS))

    pen = TTGlyphPen(None)

    pen.moveTo((50, 0))
    pen.lineTo((50, 700))
    pen.lineTo((450, 700))
    pen.lineTo((450, 0))
    pen.closePath()

    glyph = pen.glyph()

    fb.setupGlyf({n: glyph for n in order})
    fb.setupHorizontalMetrics({n: (500, 50) for n in order})
    fb.setupHorizontalHeader(ascent=800, descent=-200)
    fb.setupNameTable({"familyName": "Demo Font", "styleName": "Regular"})
    fb.setupOS2(usWeightClass=weight, fsSelection=1 if italic else 0x40)
    fb.setupPost()
    path.parent.mkdir(parents=True, exist_ok=True)
    fb.save(path)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    (tmp_path / "sources").mkdir()
    (tmp_path / "sources/font.yaml").write_text(FONT_YAML)
    (tmp_path / "OFL.txt").write_text("Copyright 2025 The Demo Font Project Authors\n")
    (tmp_path / "AUTHORS.txt").write_text("Someone\n")
    make_ttf(tmp_path / "fonts/ttf/DemoFont-Regular.ttf", 400)
    make_ttf(tmp_path / "fonts/ttf/DemoFont-Bold.ttf", 700)

    return tmp_path


def test_version_maps_to_semver():
    assert web.npm_version("1.001") == "1.1.0"
    assert web.npm_version("1.012") == "1.12.0"
    assert web.npm_version("2.000") == "2.0.0"


def test_unicode_range_is_compact():
    assert web.unicode_range({0x20, 0x21, 0x22, 0x41, 0x43, 0x44}) == "U+0020-0022,U+0041,U+0043-0044"


def test_package_name_defaults_and_override(repo):
    assert web.package_name(load_config(repo)) == "@example/demo-font"

    (repo / "sources/font.yaml").write_text(FONT_YAML + "npm: {name: '@octalmesh/demo'}\n")

    assert web.package_name(load_config(repo)) == "@octalmesh/demo"

    (repo / "sources/font.yaml").write_text(FONT_YAML + "npm: {name: 'Bad Name'}\n")

    with pytest.raises(web.WebError):
        web.package_name(load_config(repo))


def test_build_package_layout(repo):
    pkg = web.build_package(load_config(repo), repo / "dist/npm")

    assert pkg.name == "demo-font"

    names = sorted(p.name for p in pkg.iterdir())

    for expected in ("package.json", "index.css", "400.css", "700.css", "latin-400.css", "cyrillic-700.css",
                     "latin.css", "cyrillic.css", "files", "metadata.json", "OFL.txt", "AUTHORS.txt", "README.md"):
        assert expected in names, expected

    files = sorted(p.name for p in (pkg / "files").iterdir())

    assert files == ["demo-font-cyrillic-400-normal.woff2", "demo-font-cyrillic-700-normal.woff2",
                     "demo-font-latin-400-normal.woff2", "demo-font-latin-700-normal.woff2"]

    meta = json.loads((pkg / "package.json").read_text())

    assert meta["name"] == "@example/demo-font" and meta["version"] == "1.12.0"
    assert meta["license"] == "OFL-1.1" and meta["exports"]["."] == "./index.css"
    assert "CONTRIBUTORS.txt" in meta["files"] and not (pkg / "CONTRIBUTORS.txt").exists()


def test_woff2_is_a_real_subset(repo):
    pkg = web.build_package(load_config(repo), repo / "dist/npm")
    latin = TTFont(pkg / "files/demo-font-latin-400-normal.woff2")
    cyr = TTFont(pkg / "files/demo-font-cyrillic-400-normal.woff2")

    assert latin.flavor == "woff2"
    assert set(latin.getBestCmap()) == {0x20, 0x41, 0x42}
    assert set(cyr.getBestCmap()) == {0x416, 0x42F}


def test_css_contents(repo):
    pkg = web.build_package(load_config(repo), repo / "dist/npm")
    css = (pkg / "index.css").read_text()

    assert css.count("@font-face") == 2
    assert "font-family: 'Demo Font';" in css and "font-weight: 400;" in css
    assert "src: url(./files/demo-font-latin-400-normal.woff2) format('woff2');" in css
    assert "unicode-range: U+0020,U+0041-0042;" in css or "unicode-range: U+0020,U+0041-0042" in css
    assert css.index("cyrillic") < css.index("latin")
    assert "font-weight: 700;" in (pkg / "700.css").read_text()


def test_output_is_reproducible(repo):
    first = web.build_package(load_config(repo), repo / "a")
    second = web.build_package(load_config(repo), repo / "b")

    for f in (first / "files").iterdir():
        assert f.read_bytes() == (second / "files" / f.name).read_bytes()


def test_requires_fonts_and_license(repo):
    cfg = load_config(repo)

    (repo / "OFL.txt").unlink()

    with pytest.raises(web.WebError, match="OFL.txt"):
        web.build_package(cfg, repo / "dist")

    empty = repo / "fonts"

    for p in sorted(empty.rglob("*.ttf")):
        p.unlink()

    with pytest.raises(web.WebError, match="no built fonts"):
        web.build_package(cfg, repo / "dist")


def test_duplicate_faces_are_rejected(repo):
    make_ttf(repo / "fonts/ttf/DemoFont-Other.ttf", 400)

    with pytest.raises(web.WebError, match="same CSS face"):
        web.build_package(load_config(repo), repo / "dist")


def test_variable_font_gets_weight_range_and_becomes_default(repo):
    for p in (repo / "fonts/ttf").iterdir():
        p.unlink()

    path = repo / "fonts/variable/DemoFont[wght].ttf"

    make_ttf(path)

    font = TTFont(path)
    fvar = newTable("fvar")
    axis = Axis()
    axis.axisTag, axis.minValue, axis.defaultValue, axis.maxValue = "wght", 300, 400, 700
    axis.axisNameID = 256
    fvar.axes = [axis]
    fvar.instances = []
    font["fvar"] = fvar

    font["name"].setName("Weight", 256, 3, 1, 0x409)
    font.save(path)

    pkg = web.build_package(load_config(repo), repo / "dist")
    css = (pkg / "index.css").read_text()

    assert "font-weight: 300 700;" in css
    assert (pkg / "variable.css").read_text().split("\n\n", 1)[1] == css.split("\n\n", 1)[1]
    assert (pkg / "files/demo-font-latin-wght-normal.woff2").is_file()
    assert "fvar" in TTFont(pkg / "files/demo-font-latin-wght-normal.woff2")
