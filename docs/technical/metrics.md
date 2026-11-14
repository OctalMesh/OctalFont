# Metrics

All values are font units on a **1000 UPM** grid. A family sets them in
`sources/font.yaml` (see [Configuration](configuration.md)).

| Metric                | Octal Titan | Notes                                                |
|-----------------------|-------------|------------------------------------------------------|
| Units per em          | 1000        | `metrics.upm`                                        |
| Cap height            | 700         | SVG `y=0`                                            |
| x-height              | 500         |                                                      |
| Ascender              | 1050        | clears the tallest glyph and Vietnamese stacks       |
| Descender             | -300        |                                                      |
| Advance (monospace)   | 850         | 700 body + 75 + 75 side bearings                     |

## Coordinate mapping

The SVG artboard is 1000 units tall. `y = 0` is the **cap height** and `y = 1000`
is the **baseline**, so a drawing is scaled 1:1 and flipped when it becomes a
UFO glyph.

## Vertical metrics

The tool writes the same values to the typographic (`OS/2 sTypo*`), `hhea` and,
for Windows, `OS/2 usWin*` tables, and sets `USE_TYPO_METRICS`. The `win` values
are computed from the tallest and deepest glyph of the whole family.

## What `octalfont check` verifies

| Check                                      | Level  | Rule                                                        |
|--------------------------------------------|--------|-------------------------------------------------------------|
| Ascender + \|descender\|                   | WARN   | 120-130 % of the UPM is recommended by Google Fonts         |
| Capitals centred in the line               | WARN   | `ascender - cap_height == \|descender\|`                    |
| Ascender clears the tallest glyph          | WARN   | otherwise accents crowd the line                            |
| Vietnamese stack (U+1EAE) fits             | WARN   | metrics cannot change after release: decide before `1.000`  |
| Descender reaches the deepest glyph        | WARN   |                                                             |
| Win metrics                                | PASS   | reported for information                                    |

> [!IMPORTANT]
> Vertical metrics must not change after a font is published on Google Fonts. Settle
> them, and the decision about Vietnamese support, before the first release.

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
