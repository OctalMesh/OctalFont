# Licensing

OctalFont uses a **split-license** model that separates the tooling code from
the font files. Each is licensed where it lives.

> [!NOTE]
> Both code and fonts are provided **"as is"** without warranties of any kind.

## Tool - MIT License

All code, build tooling, workflows and configuration in **this** repository are
released under the [MIT License](../LICENSE.md).

You may freely use, copy, modify, merge, publish, distribute, sublicense, and/or
sell copies of the code, provided the original copyright notice and this
permission notice are included in all copies or substantial portions.

## Fonts - SIL Open Font License 1.1

Every font family is a separate repository and carries its own `OFL.txt`:

| Family                                                          | License                                    |
|-----------------------------------------------------------------|--------------------------------------------|
| [Octal Titan](https://github.com/OctalMesh/octalfont-titan)     | [SIL OFL 1.1](https://openfontlicense.org) |
| [Octal Cuprum](https://github.com/OctalMesh/octalfont-cuprum)   | [SIL OFL 1.1](https://openfontlicense.org) |
| [Octal Mercury](https://github.com/OctalMesh/octalfont-mercury) | [SIL OFL 1.1](https://openfontlicense.org) |

Key terms of the OFL:

| Permission                                    | Condition                       |
|-----------------------------------------------|---------------------------------|
| Use in any project, including commercial work | No restrictions                 |
| Embed in documents and software               | No restrictions                 |
| Modify and redistribute modified versions     | Must be released under the OFL  |
| Bundle / sell as standalone font product      | Not permitted                   |

The font files are not derived from the tool's code, so building a font with
`octalfont` does not make the result MIT-licensed: the OFL of the font repository
applies to the output.

## Reserved Font Names

The families do **not** declare a Reserved Font Name. The copyright line of each
`OFL.txt` follows the Google Fonts convention:

```text
Copyright 2025 The Octal Titan Project Authors (https://github.com/OctalMesh/octalfont-titan)
```

## Authors and contributors

Each font repository lists copyright holders in `AUTHORS.txt` (required). A
`CONTRIBUTORS.txt` is **optional**: add it only when there are contributors who are
not already in `AUTHORS.txt`. An empty placeholder is flagged by `octalfont check`.

#

###### Table of Contents

- [Index](README.md)
- [Licensing](licensing.md)
- [Releasing](../RELEASING.md)

## Design

- [Overview](design/README.md)
- [Sketches](design/sketches/README.md)

## Technical

- [Metrics](technical/metrics.md)
- [Axes](technical/axes.md)
- [Building the Fonts](technical/build.md)
- [Configuration](technical/configuration.md)
