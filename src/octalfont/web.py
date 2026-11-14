"""Build a self-hostable npm package from the built fonts (``octalfont npm``).

The package follows the layout web developers know from Fontsource, so it can be used
without any configuration, and it is a plain redistribution of the OFL-licensed font:

    <out>/<slug>/
        package.json        name, SemVer, license OFL-1.1, exports map
        index.css           default @font-face rules (all subsets, unicode-range)
        400.css, 700.css    one weight, all subsets          (static fonts)
        variable.css        the weight axis                  (variable fonts)
        latin-400.css ...   one subset of one weight
        files/*.woff2       the font files, one per subset, weight and style
        metadata.json       machine-readable summary
        OFL.txt, AUTHORS.txt, CONTRIBUTORS.txt (if any), README.md

Subsets come from the Google Fonts glyph sets the family targets (latin, cyrillic,
vietnamese), so browsers download only the scripts a page uses.
"""

from __future__ import annotations

import json
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from fontTools import subset
from fontTools.ttLib import TTFont

from . import glyphnames
from .config import FontConfig

SUBSET_ORDER = ("cyrillic", "vietnamese", "latin")
NPM_NAME = re.compile(r"^(@[a-z0-9][a-z0-9._-]*/)?[a-z0-9][a-z0-9._-]*$")


class WebError(RuntimeError):
    """The package cannot be built (no fonts, invalid name, ...)."""


# ============================================================================ #
#                                    Naming                                    #
# ============================================================================ #


def slug(cfg: FontConfig) -> str:
    """``Octal Titan`` -> ``octal-titan``."""
    return re.sub(r"[^a-z0-9]+", "-", cfg.family.lower()).strip("-")


def package_name(cfg: FontConfig) -> str:
    """``@<owner>/<slug>`` unless ``npm.name`` in font.yaml says otherwise."""

    name = cfg.npm.get("name")

    if not name:
        owner = urlparse(cfg.repository).path.strip("/").split("/")[0].lower()
        name = f"@{owner}/{slug(cfg)}" if owner else slug(cfg)

    if not NPM_NAME.match(name):
        raise WebError(f"'{name}' is not a valid npm package name")

    return name


def npm_version(font_version: str) -> str:
    """Map a Google Fonts version to SemVer: ``1.001`` -> ``1.1.0``, ``2.000`` -> ``2.0.0``."""

    major, minor = font_version.split(".")

    return f"{int(major)}.{int(minor)}.0"


# ============================================================================ #
#                                   Subsets                                    #
# ============================================================================ #


def subset_of(glyphset: str) -> str:
    low = glyphset.lower()

    if "vietnamese" in low:
        return "vietnamese"

    if "cyrillic" in low:
        return "cyrillic"

    if "latin" in low:
        return "latin"

    return re.sub(r"^gf_", "", low)


def unicode_range(codepoints: set[int]) -> str:
    """Compact CSS ``unicode-range`` value: ``U+0020-007E,U+00A0``."""
    out, run = [], []

    for cp in sorted(codepoints):
        if run and cp == run[-1] + 1:
            run.append(cp)
            continue

        if run:
            out.append(run)

        run = [cp]

    if run:
        out.append(run)

    return ",".join(f"U+{r[0]:04X}" if len(r) == 1 else f"U+{r[0]:04X}-{r[-1]:04X}" for r in out)


def subset_codepoints(cfg: FontConfig, available: set[int]) -> dict[str, set[int]]:
    """Codepoints of each subset that the font really contains (latin wins overlaps)."""

    groups: dict[str, set[int]] = {}

    for gs in [*cfg.required_glyphsets, *cfg.optional_glyphsets]:
        groups.setdefault(subset_of(gs), set()).update(glyphnames.glyphset_unicodes(gs))

    latin = groups.get("latin", set())
    result = {}

    for name, cps in groups.items():
        cps = (cps - latin if name != "latin" else cps) & available
        cps.discard(0)

        if cps:
            result[name] = cps

    return dict(sorted(result.items(), key=lambda kv: SUBSET_ORDER.index(kv[0]) if kv[0] in SUBSET_ORDER else -1))


# ============================================================================ #
#                                    Fonts                                     #
# ============================================================================ #


@dataclass
class Face:
    path: Path
    weight: tuple[int, int]                # (min, max); equal for a static font
    italic: bool
    variable: bool
    stretch: tuple[int, int] | None = None # wdth axis percentages, variable fonts only

    @property
    def weight_css(self) -> str:
        lo, hi = self.weight
        return str(lo) if lo == hi else f"{lo} {hi}"

    @property
    def key(self) -> str:
        """``400`` / ``variable``; with ``-italic`` for italic faces."""
        base = "variable" if self.variable else str(self.weight[0])
        return base + ("-italic" if self.italic else "")

    @property
    def file_tag(self) -> str:
        base = "wght" if self.variable else str(self.weight[0])
        return f"{base}-{'italic' if self.italic else 'normal'}"


def read_face(path: Path) -> Face:
    with TTFont(path, lazy=True, recalcTimestamp=False) as font:
        italic = bool(font["OS/2"].fsSelection & 1) or bool(font["head"].macStyle & 2)

        if "fvar" in font:
            axes = {a.axisTag: a for a in font["fvar"].axes}
            w = axes.get("wght")
            weight = (round(w.minValue), round(w.maxValue)) if w else (font["OS/2"].usWeightClass,) * 2
            d = axes.get("wdth")
            stretch = (round(d.minValue), round(d.maxValue)) if d else None

            return Face(path, weight, italic, True, stretch)

        return Face(path, (font["OS/2"].usWeightClass,) * 2, italic, False)


def find_faces(cfg: FontConfig) -> list[Face]:
    fonts = cfg.root / "fonts"
    paths = sorted(fonts.rglob("*.ttf")) if fonts.is_dir() else []

    if not paths:
        raise WebError(f"no built fonts in {fonts}; run `octalfont build` first")

    faces = sorted((read_face(p) for p in paths), key=lambda f: (f.variable, f.italic, f.weight))
    keys = [f.key for f in faces]
    dupes = {k for k in keys if keys.count(k) > 1}

    if dupes:
        raise WebError(f"several fonts map to the same CSS face: {', '.join(sorted(dupes))}")

    return faces


def cmap_of(path: Path) -> set[int]:
    with TTFont(path, lazy=True) as font:
        return set(font["cmap"].getBestCmap())


def write_woff2(src: Path, dst: Path, codepoints: set[int]) -> None:
    options = subset.Options()
    options.layout_features = ["*"]
    options.name_IDs = ["*"]
    options.notdef_outline = True
    options.hinting = True
    options.glyph_names = False
    options.flavor = "woff2"

    with TTFont(src, recalcTimestamp=False) as font:
        subsetter = subset.Subsetter(options)

        subsetter.populate(unicodes=sorted(codepoints))
        subsetter.subset(font)

        font.flavor = "woff2"

        dst.parent.mkdir(parents=True, exist_ok=True)
        font.save(dst)


# ============================================================================ #
#                                     CSS                                      #
# ============================================================================ #


def font_face(cfg: FontConfig, face: Face, sub: str, codepoints: set[int], stem: str) -> str:
    lines = [
        "@font-face {",
        f"  font-family: '{cfg.family}';",
        f"  font-style: {'italic' if face.italic else 'normal'};",
        "  font-display: swap;",
        f"  font-weight: {face.weight_css};",
    ]
    if face.stretch and face.stretch[0] != face.stretch[1]:
        lines.append(f"  font-stretch: {face.stretch[0]}% {face.stretch[1]}%;")
    lines += [
        f"  src: url(./files/{stem}-{sub}-{face.file_tag}.woff2) format('woff2');",
        f"  unicode-range: {unicode_range(codepoints)};",
        "}",
    ]
    return "\n".join(lines)


def banner(cfg: FontConfig, what: str) -> str:
    return f"/* {cfg.family} {cfg.version} - {what}\n * {cfg.copyright}\n * SIL Open Font License 1.1 - see OFL.txt */\n"


# ============================================================================ #
#                                   Package                                    #
# ============================================================================ #


def readme(cfg: FontConfig, name: str, version: str, faces: list[Face], subsets: list[str]) -> str:
    default = next((f for f in faces if f.variable and not f.italic), faces[0])
    weights = ", ".join(sorted({f.weight_css for f in faces}))
    variable = any(f.variable for f in faces)
    one = default.key if not default.variable else "variable"
    css = f"{cfg.family}"

    return f"""# {cfg.family}

{cfg.description}

Self-hosted web font package of **{cfg.family}** (WOFF2, split by script). The files ship
inside your project, so no request goes to a third-party font server.

## Install

```sh
npm install {name}
```

## Use

Import the stylesheet once, anywhere your bundler accepts CSS (Vite, webpack, Next.js, Astro, ...):

```js
import "{name}";                 // default face, all subsets
```

```css
body {{
  font-family: '{css}', monospace;
}}
```

Other entry points:

| Import | Contents |
|---|---|
| `{name}` | the default face ({one}), all subsets |
| `{name}/{one}.css` | {"the variable weight axis" if default.variable else "one weight"}, all subsets |
| `{name}/{subsets[0]}.css` | the default face, **{subsets[0]}** subset only |
| `{name}/files/*.woff2` | the raw font files, for your own `@font-face` |

Available weights: {weights}. Subsets: {", ".join(subsets)}. {"The font is variable: any weight in the range works with `font-weight`." if variable else ""}

No bundler? Link the stylesheet from `node_modules` or copy `files/` and the CSS next to your pages.

## Versioning

Package version `{version}` ships font version `{cfg.version}` (`MAJOR.MINOR` of the font
becomes `MAJOR.MINOR.0`: font `1.001` is package `1.1.0`).

## License

{cfg.copyright}

Licensed under the [SIL Open Font License 1.1](OFL.txt). The files in this package are
format conversions and script subsets of the fonts released at
[{cfg.repository}]({cfg.repository}).
"""


def build_package(cfg: FontConfig, out_dir: Path) -> Path:
    """Write the npm package directory ``<out_dir>/<slug>`` and return it."""
    name = package_name(cfg)
    version = npm_version(cfg.version)
    faces = find_faces(cfg)
    stem = slug(cfg)

    pkg = out_dir / stem

    if pkg.exists():
        shutil.rmtree(pkg)

    (pkg / "files").mkdir(parents=True)

    available = set().union(*(cmap_of(f.path) for f in faces))
    subsets = subset_codepoints(cfg, available)

    if not subsets:
        raise WebError("none of the glyph sets of font.yaml is present in the built fonts")

    css_files: dict[str, list[str]] = {}

    for face in faces:
        blocks = []

        for sub, cps in subsets.items():
            have = cps & cmap_of(face.path)

            if not have:
                continue

            write_woff2(face.path, pkg / "files" / f"{stem}-{sub}-{face.file_tag}.woff2", have)

            block = font_face(cfg, face, sub, have, stem)

            blocks.append(block)
            css_files[f"{sub}-{face.key}.css"] = [block]

        css_files[f"{face.key}.css"] = blocks

    default = next((f for f in faces if f.variable and not f.italic),
                   next((f for f in faces if not f.italic and f.weight[0] == 400), faces[0]))
    css_files["index.css"] = css_files[f"{default.key}.css"]

    for sub in subsets:
        key = f"{sub}-{default.key}.css"

        if key in css_files:
            css_files[f"{sub}.css"] = css_files[key]

    for fname, blocks in css_files.items():
        (pkg / fname).write_text(banner(cfg, fname) + "\n" + "\n\n".join(blocks) + "\n", encoding="utf-8", newline="\n")

    package = {
        "name": name,
        "version": version,
        "description": cfg.description or f"{cfg.family} web font",
        "license": "OFL-1.1",
        "author": {"name": cfg.designer, **({"url": cfg.designer_url} if cfg.designer_url else {})},
        "homepage": cfg.repository,
        "repository": {"type": "git", "url": f"git+{cfg.repository}.git"},
        "bugs": {"url": f"{cfg.repository}/issues"},
        "keywords": ["font", "fonts", "woff2", "self-hosted", "typography", "octal", stem, *subsets],
        "sideEffects": ["*.css"],
        "style": "index.css",
        "exports": {
            ".": "./index.css",
            "./*.css": "./*.css",
            "./files/*": "./files/*",
            "./metadata.json": "./metadata.json",
            "./package.json": "./package.json",
        },
        "files": ["*.css", "files/", "metadata.json", "OFL.txt", "AUTHORS.txt", "CONTRIBUTORS.txt", "README.md"],
        "publishConfig": {"access": "public", "provenance": True},
    }
    package.update(cfg.npm.get("package", {}) or {})  # escape hatch for extra fields
    (pkg / "package.json").write_text(json.dumps(package, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    metadata = {
        "family": cfg.family,
        "fontVersion": cfg.version,
        "packageVersion": version,
        "license": "OFL-1.1",
        "defaultFace": default.key,
        "faces": [{"key": f.key, "weight": f.weight_css, "style": "italic" if f.italic else "normal",
                   "variable": f.variable} for f in faces],
        "subsets": {s: unicode_range(c) for s, c in subsets.items()},
    }
    (pkg / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    (pkg / "README.md").write_text(readme(cfg, name, version, faces, list(subsets)), encoding="utf-8", newline="\n")

    for legal in ("OFL.txt", "AUTHORS.txt", "CONTRIBUTORS.txt"):
        if (cfg.root / legal).is_file():
            shutil.copy2(cfg.root / legal, pkg / legal)

    if not (pkg / "OFL.txt").is_file():
        raise WebError("OFL.txt is missing: the license must travel with the font files")

    return pkg
