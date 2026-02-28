# Design Overview of OctalFont

OctalFont is a geometric, constraint-driven typeface family built as part of
the [OctalMesh](https://octalmesh.com) design system.

## Core Principles

### Hand-Drawn Origin

Every glyph starts as a pencil sketch in a physical sketchbook. Proportions,
stroke rhythm, and geometric logic are resolved on paper before any vector
work begins. The sketch is then redrawn in **Adobe Illustrator** and saved
under `sources/<family>/ai/` before being exported to SVG for the build
pipeline.

### Strict Geometry

Every glyph is constructed from a limited set of geometric primitives:
straight lines, circular arcs, and right-angle corners. No freehand curves.
This constraint forces consistency across all glyphs and makes the family
unmistakably modular.

### Reproducibility

The build pipeline converts each SVG to a UFO glyph deterministically.
Given the same source SVG and the same `metrics.yaml`, the output font is
byte-for-byte reproducible. No manual post-processing is required after
the initial glyph is drawn.

### System Integration

OctalFont is designed to complement other OctalMesh visual assets. Stroke
weights, optical sizes, and spacing decisions are informed by the broader
design token system, not by traditional type-design conventions alone.

## Visual Character

Each family's name is not decorative - it directly maps to the physical
properties of the material it is named after:

- **Titan _(Titanium)_** - heavy, unyielding, structural. The logotype-grade
  anchor of the family. Used for all base OctalMesh products and branding where
  solidity and authority are needed.
- **Cuprum _(Copper)_** - practical, workman-like, adaptable. A thin,
  regular-weight monospaced typeface with flexible axis settings for UI, code,
  and body copy contexts.
- **Mercury _(Quicksilver)_** - derived from Titan but with all sharp corners
  replaced by smooth, fluid curves. Intended for portfolio sites and
  advertising materials where a minimalist, rounded aesthetic is required.

## Families at a Glance

| Family  | Visual character                                       | Primary use                                   |
|---------|--------------------------------------------------------|-----------------------------------------------|
| Titan   | Heavy, solid, logotype-grade. Strength and permanence. | Logos, headlines, all base OctalMesh products |
| Cuprum  | Thin, neutral, flexible via axis settings.             | UI, code, body copy                           |
| Mercury | Fluid, smooth, rounded strokes. Derived from Titan.    | Portfolio, rounded / minimalist product lines |

#

###### Table of Contents

- [Index](../README.md)
- [Licensing](../licensing.md)

## Design

- [Overview](README.md)
- [Sketches](sketches/README.md)

## Technical

- [Metrics](../technical/metrics.md)
- [Axes](../technical/axes.md)
- [Building the Font](../technical/build.md)
