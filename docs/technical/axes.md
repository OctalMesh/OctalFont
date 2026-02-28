# Axes

OctalFont follows the [OpenType variable font](https://docs.microsoft.com/typography/opentype/spec/dvaraxisreg)
axis specification. This page documents both the currently active axes and
the planned additions.

## Adding a New Axis

1. Add the axis definition to `OctalFont-Titan.designspace` inside `<axes>`
2. Add a matching `<location>` element to every `<source>` and `<instance>`
3. Verify master compatibility with `checkCompatibility: true`
4. Update the `build*` flags in `config.yaml` as needed

#

###### Table of Contents

- [Index](../README.md)
- [Licensing](../licensing.md)

## Design

- [Overview](../design/README.md)
- [Sketches](../design/sketches/README.md)

## Technical

- [Metrics](metrics.md)
- [Axes](axes.md)
- [Building the Font](build.md)
