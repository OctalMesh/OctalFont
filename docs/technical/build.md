# Building the Fonts

Fonts are built with the `octalfont` command-line tool from the SVG drawings
kept in a font repository. The tool is a Python package (Python 3.10 or newer);
a font repository pins the exact tool version it was built with in its own
`requirements.txt`.

## Prerequisites

| Requirement  | Why                                                               |
|--------------|-------------------------------------------------------------------|
| Python 3.10+ | runs the tool                                                     |
| Git          | submodules, changesets and the release commands                   |
| A venv       | keeps the font tooling away from your system Python (recommended) |

`gftools`, `fontmake` and Font Bakery come with the `build` extra and need no
manual setup.

## Install

### Inside a font repository (recommended)

The repository already pins the tool:

```sh
git clone https://github.com/OctalMesh/octalfont-titan && cd octalfont-titan
python -m venv .venv
. .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### In the OctalFont monorepo (working on the tool and the fonts together)

```sh
git clone --recurse-submodules https://github.com/OctalMesh/OctalFont && cd OctalFont
python -m venv .venv && . .venv/bin/activate
pip install -e ".[build,test]"   # editable: changes to src/ apply immediately
```

Forgot `--recurse-submodules`? Run `git submodule update --init`.

## Commands

Run them from the font repository root, or point the tool at one with `-C`:

```sh
octalfont -C fonts/titan check
```

| Command                      | What it does                                                                       |
|------------------------------|------------------------------------------------------------------------------------|
| `octalfont sources`          | `sources/svg` -> UFO masters, composite glyphs, designspace and `config.yaml`      |
| `octalfont check`            | legal files, vertical metrics and glyph-set coverage                               |
| `octalfont check --missing`  | the same, plus the names of every missing glyph                                    |
| `octalfont build`            | `sources` + gftools builder + `meta` table; output in `fonts/`                     |
| `octalfont package`          | zips `fonts/` and the legal files into `dist/<Family>-vX.YYY.zip`                  |
| `octalfont npm`              | builds the npm package (`dist/npm/<slug>/`: WOFF2 per script, CSS, `package.json`) |
| `octalfont postprocess FILE` | adds the `meta` table to an already built TTF                                      |
| `octalfont release ...`      | changesets, versioning and release gates, see [RELEASING.md](../../RELEASING.md)   |

`check` exits with a non-zero status only on `FAIL`; `WARN` lines are advisory.

## Typical session

```sh
octalfont sources            # after editing an SVG, composites.yaml or font.yaml
octalfont check --missing    # check for missing glyphs and vertical metrics
octalfont build              # fonts/ttf/*.ttf (and fonts/variable/ for variable families)
git add sources && git commit
```

`sources/ufo/`, `*.designspace` and `sources/config.yaml` are generated but committed:
Google Fonts needs the sources in the repository, and CI fails when they are stale.

## Web package

`octalfont npm` turns the built TTFs into a package that developers install with npm:

```sh
octalfont build
octalfont npm                    # -> dist/npm/octal-titan/
cd dist/npm/octal-titan && npm pack --dry-run
```

The package has WOFF2 files per script and weight (`files/`), CSS with
`unicode-range` (`index.css`, `400.css`, `latin.css`, `variable.css` ...),
`metadata.json`, the OFL and a README. Scripts come from the glyph sets in
`font.yaml` (`latin`, `cyrillic`, `vietnamese`); a variable font gets a
`font-weight` range. The package version maps the font version: `1.001` becomes
`1.1.0`. The package name defaults to `@<github owner>/<family-slug>` and can be
changed with `npm.name` in `font.yaml` (see [Configuration](configuration.md)).

## Reproducible builds

Set `SOURCE_DATE_EPOCH` to get identical bytes on every run (fonts, the zip and
the WOFF2 files). CI uses `0`.

```sh
SOURCE_DATE_EPOCH=0 octalfont build
```

## Troubleshooting

| Symptom                           | Fix                                                                        |
|-----------------------------------|----------------------------------------------------------------------------|
| `gftools not found`               | install the `build` extra: `pip install "octalfont[build]"`                |
| CI: "Generated sources are stale" | run `octalfont sources` and commit `sources/`                              |
| `fonts/` is empty after `build`   | read the gftools output above the error; the build did not finish          |
| `check` reports missing glyphs    | `octalfont check --missing`, then draw them in `sources/ai` and export SVG |

#

###### Table of Contents

- [Index](../README.md)
- [Licensing](../licensing.md)
- [Releasing](../../RELEASING.md)

## Design

- [Overview](../design/README.md)
- [Sketches](../design/sketches/README.md)

## Technical

- [Metrics](../technical/metrics.md)
- [Axes](../technical/axes.md)
- [Building the Fonts](../technical/build.md)
- [Configuration](../technical/configuration.md)
