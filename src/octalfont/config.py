"""Typed loader for a font project's ``sources/font.yaml``.

``font.yaml`` is the single source of truth for a family: names, version,
legal strings, metrics, spacing and glyph-set targets. Everything else
(UFO info, designspace, gftools ``config.yaml``) is generated from it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

# Canonical GF strings (https://googlefonts.github.io/gf-guide/requirements.html).
OFL_LICENSE = (
    "This Font Software is licensed under the SIL Open Font License, "
    "Version 1.1. This license is available with a FAQ at: https://openfontlicense.org"
)
OFL_URL = "https://openfontlicense.org"

WEIGHT_NAMES = {
    100: "Thin",
    200: "ExtraLight",
    300: "Light",
    400: "Regular",
    500: "Medium",
    600: "SemiBold",
    700: "Bold",
    800: "ExtraBold",
    900: "Black",
}


class ConfigError(ValueError):
    """Raised when font.yaml is missing, malformed or violates GF rules."""


@dataclass
class Master:
    style: str
    weight: int
    svg: str  # directory with the glyph SVGs, relative to sources/


@dataclass
class Metrics:
    upm: int = 1000
    cap_height: int = 700
    x_height: int = 500
    ascender: int = 1000
    descender: int = -300
    underline_position: int = -100
    underline_thickness: int = 50


@dataclass
class Spacing:
    mode: str = "monospace"        # "monospace" | "proportional"
    advance: int = 850             # monospace advance width
    lsb: int = 75                  # proportional: side bearings added around the SVG body
    rsb: int = 75
    zero_width_marks: bool = True  # combining marks (Mn) get advance 0


@dataclass
class SvgSettings:
    artboard: float = 1000.0  # SVG artboard side; y=0 is cap height, y=artboard is baseline


@dataclass
class FontConfig:
    root: Path                      # repository root
    sources: Path                   # <root>/sources
    family: str
    version: str
    copyright_year: int
    repository: str
    vendor_id: str
    designer: str
    designer_url: str
    manufacturer: str
    manufacturer_url: str
    description: str = ""
    masters: list[Master] = field(default_factory=list)
    metrics: Metrics = field(default_factory=Metrics)
    spacing: Spacing = field(default_factory=Spacing)
    svg: SvgSettings = field(default_factory=SvgSettings)
    required_glyphsets: list[str] = field(default_factory=lambda: ["GF_Latin_Core"])
    optional_glyphsets: list[str] = field(default_factory=list)
    scripts: list[str] = field(default_factory=lambda: ["Latn"])
    build: dict[str, Any] = field(default_factory=dict)
    composites_file: str = "composites.yaml"
    features_file: str = "features.fea"
    npm: dict[str, Any] = field(default_factory=dict)  # optional overrides for `octalfont npm`

    @property
    def copyright(self) -> str:
        return f"Copyright {self.copyright_year} The {self.family} Project Authors ({self.repository})"

    @property
    def file_stem(self) -> str:
        """``Octal Titan`` -> ``OctalTitan``"""
        return self.family.replace(" ", "")

    @property
    def version_major_minor(self) -> tuple[int, int]:
        major, minor = self.version.split(".")
        return int(major), int(minor)

    def ps_name(self, style: str) -> str:
        return f"{self.file_stem}-{style.replace(' ', '')}"


_CAMEL = re.compile(r"[a-z][A-Z]")


def validate_family_name(family: str, styles: list[str]) -> list[str]:
    """Return GF naming-rule violations for a family name (empty list = OK)."""
    problems: list[str] = []

    if not re.fullmatch(r"[A-Za-z0-9 ]+", family):
        problems.append("family name must be ASCII letters/digits/spaces only (no hyphens, underscores, accents)")

    if _CAMEL.search(family):
        problems.append("family name must not use camelCase; separate words with spaces")

    if family.isupper():
        problems.append("family name must not be all caps")

    longest = max((len(f"{family} {s}") for s in styles), default=len(family))

    if longest > 32:
        problems.append(f"family + style name is {longest} chars; GF limit is 32")

    if re.search(r"colou?r|colr", family, re.I):
        problems.append("family name must not contain 'color'/'colr'")

    return problems


def _require(data: dict, key: str) -> Any:
    if key not in data or data[key] in (None, ""):
        raise ConfigError(f"font.yaml: missing required key '{key}'")

    return data[key]


def load_config(path: str | Path) -> FontConfig:
    """Load and validate ``font.yaml``. ``path`` may be the file or the repo root."""

    path = Path(path).resolve()

    if path.is_dir():
        path = path / "sources" / "font.yaml"

    if not path.is_file():
        raise ConfigError(f"font.yaml not found: {path}")

    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    sources = path.parent
    root = sources.parent

    masters = [Master(**m) for m in data.get("masters", [])] or [
        Master(style="Regular", weight=400, svg="svg")
    ]
    glyphsets = data.get("glyphsets", {}) or {}

    cfg = FontConfig(
        root=root,
        sources=sources,
        family=_require(data, "family"),
        version=str(_require(data, "version")),
        copyright_year=int(_require(data, "copyright_year")),
        repository=_require(data, "repository"),
        vendor_id=str(_require(data, "vendor_id")),
        designer=_require(data, "designer"),
        designer_url=data.get("designer_url", ""),
        manufacturer=data.get("manufacturer", ""),
        manufacturer_url=data.get("manufacturer_url", ""),
        description=data.get("description", ""),
        masters=masters,
        metrics=Metrics(**(data.get("metrics") or {})),
        spacing=Spacing(**(data.get("spacing") or {})),
        svg=SvgSettings(**(data.get("svg") or {})),
        required_glyphsets=glyphsets.get("required", ["GF_Latin_Core"]),
        optional_glyphsets=glyphsets.get("optional", []),
        scripts=data.get("scripts", ["Latn"]),
        build=data.get("build", {}) or {},
        composites_file=data.get("composites", "composites.yaml"),
        features_file=data.get("features", "features.fea"),
        npm=data.get("npm", {}) or {},
    )

    problems = validate_family_name(cfg.family, [m.style for m in cfg.masters])

    if not re.fullmatch(r"\d+\.\d{3}", cfg.version):
        problems.append(f"version '{cfg.version}' must look like MAJOR.MINOR with 3 digits, e.g. 1.000")

    if len(cfg.vendor_id) != 4 or not cfg.vendor_id.isascii():
        problems.append("vendor_id must be exactly 4 ASCII characters")

    if problems:
        raise ConfigError("font.yaml invalid:\n  - " + "\n  - ".join(problems))

    return cfg
