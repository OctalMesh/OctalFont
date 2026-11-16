"""``octalfont`` command line interface."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

from . import __version__, release
from .check import check_coverage, check_legal, check_metrics
from .config import ConfigError, load_config
from .pipeline import build_sources, vietnamese_estimate
from .web import WebError


def _cfg(args):
    from . import glyphnames

    cfg = load_config(Path(args.project))

    glyphnames.PROJECT_GLYPHSET_DIR = cfg.sources / "glyphsets"

    return cfg


def cmd_sources(args) -> int:
    cfg = _cfg(args)
    res = build_sources(cfg)

    for style, rep in res["reports"].items():
        print(f"{style}: {len(res['ufos'][style])} glyphs, {len(rep['built'])} composites built, "
              f"{len(rep['missing_parts'])} skipped (missing base/marks)")

    for w in res["warnings"]:
        print("warning:", w)

    print(f"wrote {res['designspace'].relative_to(cfg.root)} and {res['config'].relative_to(cfg.root)}")

    return 0


def cmd_check(args) -> int:
    cfg = _cfg(args)
    res = build_sources(cfg) if args.rebuild else None

    from ufoLib2 import Font

    from .pipeline import ufo_path

    default = next((m for m in cfg.masters if m.weight == 400), cfg.masters[0])
    path = ufo_path(cfg, default.style)

    if res is None and not path.exists():
        res = build_sources(cfg)

    ufo = res["ufos"][default.style] if res else Font.open(path)

    from .composites import CompositeConfig

    comp = CompositeConfig.load(cfg.sources / cfg.composites_file)
    findings = check_legal(cfg)
    layer = ufo.layers.defaultLayer
    deepest = min((b[1] for g in ufo if (b := g.getBounds(layer))), default=0)
    win = (ufo.info.openTypeOS2WinAscent, -ufo.info.openTypeOS2WinDescent)
    stack = vietnamese_estimate(ufo, comp)
    tallest = max((b[3] for g in ufo if (b := g.getBounds(layer))), default=0)
    findings += check_metrics(cfg, stack, win, deepest, tallest)
    cov, missing = check_coverage(ufo, cfg)
    findings += cov

    for f in findings:
        print(f)

    if args.missing:
        for gs, names in missing.items():
            print(f"\n{gs}: missing {len(names)}\n  " + " ".join(names))

    return 1 if any(f.level == "FAIL" for f in findings) else 0


def cmd_postprocess(args) -> int:
    from .post import add_meta

    cfg = _cfg(args)

    for f in args.fonts:
        add_meta(Path(f), cfg.scripts)
        print("meta table added:", f)

    return 0


def cmd_build(args) -> int:
    cfg = _cfg(args)

    build_sources(cfg)

    builder = shutil.which("gftools")

    if not builder:
        print("gftools not found. Install the build extra: pip install 'octalfont[build]'", file=sys.stderr)
        return 2

    subprocess.run([builder, "builder", str(cfg.sources / "config.yaml")], check=True)

    fonts = sorted((cfg.root / "fonts").rglob("*.ttf"))

    from .post import add_meta

    for f in fonts:
        add_meta(f, cfg.scripts)

    print(f"built {len(fonts)} TTF file(s) in fonts/")

    return 0


def cmd_package(args) -> int:
    from .package import make_archive

    cfg = _cfg(args)
    out = make_archive(cfg, Path(args.out))

    print(out)

    return 0


def cmd_npm(args) -> int:
    from .web import build_package

    cfg = _cfg(args)

    print(build_package(cfg, Path(args.out)))

    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="octalfont", description=__doc__)

    p.add_argument("--version", action="version", version=__version__)
    p.add_argument("-C", "--project", default=".", help="font repository root or path to font.yaml")

    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("sources", help="SVG -> UFO, composites, designspace, gftools config").set_defaults(fn=cmd_sources)

    c = sub.add_parser("check", help="check legal files, metrics and glyph coverage against GF")

    c.add_argument("--rebuild", action="store_true")
    c.add_argument("--missing", action="store_true", help="list missing glyph names")
    c.set_defaults(fn=cmd_check)

    pp = sub.add_parser("postprocess", help="add meta table to built fonts")

    pp.add_argument("fonts", nargs="+")
    pp.set_defaults(fn=cmd_postprocess)
    sub.add_parser("build", help="sources + gftools builder + postprocess").set_defaults(fn=cmd_build)

    pk = sub.add_parser("package", help="zip fonts/ and legal files in the Google Fonts upstream layout")

    pk.add_argument("--out", default="dist", help="output directory (default: dist)")
    pk.set_defaults(fn=cmd_package)

    nm = sub.add_parser("npm", help="build a self-hostable npm package (WOFF2 + CSS) from fonts/")

    nm.add_argument("--out", default="dist/npm", help="output directory (default: dist/npm)")
    nm.set_defaults(fn=cmd_npm)
    release.register(sub)

    args = p.parse_args(argv)

    try:
        return args.fn(args)
    except (ConfigError, release.ReleaseError, WebError) as e:
        print(e, file=sys.stderr)
        return 2
