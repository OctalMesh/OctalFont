# Axes

OctalFont follows the [OpenType variable font](https://docs.microsoft.com/typography/opentype/spec/dvaraxisreg)
axis specification. This page documents the currently active axes and the
planned additions.

## Current state

| Family  | Masters                                           | Output                            |
|---------|---------------------------------------------------|-----------------------------------|
| Titan   | Regular (400)                                     | static TTF in `fonts/ttf/`        |
| Cuprum  | Light 300, Regular 400, Bold 700 (in development) | variable TTF in `fonts/variable/` |
| Mercury | in development                                    | static TTF in `fonts/ttf/`        |

## Adding a master or an axis

The designspace and the `gftools` configuration are **generated**; never edit them.

1. Add a master to `masters:` in `sources/font.yaml` with its `weight` and an `svg`
   directory under `sources/` that holds that master's drawings
2. Draw the glyphs for the new master with identical names and compatible outlines
3. Run `octalfont sources`: it writes the UFO, the designspace and `config.yaml`
4. Run `octalfont check` and `octalfont build`; with more than one master the build
   produces a variable font in `fonts/variable/`
5. Add a changeset (`octalfont release add --bump major`): a new axis is a new product
   version for Google Fonts

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
