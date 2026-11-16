# Configuration

A font repository is described by three small files. Everything else in
`sources/` is generated.

| File                                           | Owner     | Purpose                                                          |
|------------------------------------------------|-----------|------------------------------------------------------------------|
| `sources/font.yaml`                            | you       | names, version, metrics, spacing, glyph sets, build options      |
| `sources/composites.yaml`                      | you       | placement of accents and other composite glyphs                  |
| `sources/features.fea`                         | you       | hand-written OpenType features (marks and kerning are generated) |
| `.changeset/config.json`                       | you       | how `octalfont release` versions this repository                 |
| `sources/ufo/`, `*.designspace`, `config.yaml` | generated | output of `octalfont sources`; committed                         |

## `sources/font.yaml`

```yaml
family: Octal Titan
version: "1.000" # MAJOR.MINOR, three-digit minor; bumped by the release flow
copyright_year: 2025
repository: https://github.com/OctalMesh/octalfont-titan
vendor_id: OCTM
designer: Nykon Hrytsyshyn
designer_url: https://nykon.me
manufacturer: OctalMesh
manufacturer_url: https://octalmesh.com
description: One sentence about the family.

masters:
  - style: Regular
    weight: 400
    svg: svg

glyphsets:
  required: [GF_Latin_Core]    # missing glyphs here FAIL the check
  optional: [GF_Cyrillic_Plus] # missing glyphs here only WARN

scripts: [Latn, Cyrl]          # written to the `meta` table

svg:
  artboard: 1000               # y=0 is the cap height, y=artboard the baseline

spacing:
  mode: monospace              # or proportional
  advance: 850
  zero_width_marks: true

metrics:
  upm: 1000
  cap_height: 700
  x_height: 500
  ascender: 1050
  descender: -300

build:
  buildOTF: false
  buildWebfont: false

npm:                             # optional, for `octalfont npm`
  name: "@octalmesh/octal-titan" # default: @<github owner>/<family-slug>
```

| Key            | Notes                                                                                                |
|----------------|------------------------------------------------------------------------------------------------------|
| `version`      | Never edit by hand after the first release: the release flow owns it                                 |
| `masters`      | One entry per weight; more than one makes `build` produce a variable font                            |
| `glyphsets`    | Names of the lists shipped with the tool: `GF_Latin_Core`, `GF_Latin_Vietnamese`, `GF_Cyrillic_Plus` |
| `metrics`      | Cannot change after release; settle them (and Vietnamese) before `1.000`                             |
| `npm.name`     | npm package name; must be a valid scoped or unscoped npm name                                        |
| `spacing.mode` | `monospace` uses `advance`; `proportional` adds `lsb` / `rsb` around the SVG body                    |

A project may put its own glyph-set lists into `sources/glyphsets/`; they take
precedence over the built-in ones.

## `sources/composites.yaml`

Precomposed letters are derived from Unicode decompositions. Tune placement
here, all values in font units:

```yaml
gap: 40       # base -> first mark
stack_gap: 20 # mark -> next stacked mark
marks:
  cedillacomb:
    gap: 0
overrides:
  Aacute:
    acutecomb:
      dx: 10
anchors:
  J:
    top: [310, 700]
exclude: [Lcaron, dcaron, lcaron, tcaron] # never auto-built: draw them as SVG
glyphs:
  dcaron:
    base: d
    marks: [caroncomb]
```

## `.changeset/config.json`

```json
{
  "name": "octalfont-titan",
  "scheme": "font",
  "versionFile": "sources/font.yaml",
  "baseBranch": "dev",
  "releaseBranch": "release",
  "tagPrefix": "v",
  "changelog": "CHANGELOG.md",
  "paths": ["sources/**"]
}
```

| Key           | Meaning                                                                     |
|---------------|-----------------------------------------------------------------------------|
| `name`        | key used in changeset front matter and the `CHANGELOG.md` title             |
| `scheme`      | `semver` (`X.Y.Z`, the tool) or `font` (`MAJOR.MINOR`, fonts)               |
| `versionFile` | file holding the version: `pyproject.toml` or `sources/font.yaml`           |
| `paths`       | globs that require a changeset in pull requests (`octalfont release check`) |

## Environment

| Variable            | Effect                                                              |
|---------------------|---------------------------------------------------------------------|
| `SOURCE_DATE_EPOCH` | fixed timestamps for reproducible fonts and archives                |

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
