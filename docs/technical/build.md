# Building the Font

The OctalFont build pipeline is orchestrated by the `octalfont` CLI, a Bash
script that wraps `gftools builder`, `fontbakery`, and `diffenator2`.

## Prerequisites

| Tool   | Required version | Notes                                       |
|--------|------------------|---------------------------------------------|
| Python | \>= 3.9          | `python3` or `python`                       |
| pip    | any              | Bundled with Python                         |
| ninja  | any              | Used internally by fontmake                 |
| Bash   | \>= 4.0          | Git Bash on Windows, native on Unix / macOS |

All Python dependencies (fontmake, gftools, fontbakery, diffenator2) are
installed automatically into a project-local virtualenv during setup.

## First-Time Setup

Create the virtualenv, compile lock files, and install all dependencies:

```bash
octalfont env --setup
```

Verify the environment is ready:

```bash
octalfont env
```

The virtualenv is created at `.venv/` in the repository root and is activated
automatically whenever a build or test command is run.

> [!NOTE]
> `requirements.txt` is git-ignored and never committed. `octalfont env --setup`
> compiles it automatically from `requirements.in` on every run, so the
> environment is always up to date after setup.

## Build Commands

Build all families marked as 'active' in sources/config.yaml:

```bash
octalfont build --all
```

Build a single family by its ID:

```bash
octalfont build --family=titan
octalfont build --family=cuprum
octalfont build --family=mercury
```

Build without running fontbakery QA afterwards:

```bash
octalfont build --all --no-qa
```

Build with verbose (DEBUG-level) output:

```bash
octalfont build --family=titan --verbose
```

## Build Targets

For each family the following files are produced under `fonts/<FamilyName>/`:

| Target          | Flag            | Output                 |
|-----------------|-----------------|------------------------|
| Static TrueType | `buildTTF`      | `ttf/*.ttf`            |
| Static OpenType | `buildOTF`      | `otf/*.otf`            |
| Web fonts       | `buildWebfont`  | `webfonts/*.woff2`     |
| Variable font   | `buildVariable` | `variable/*[wght].ttf` |

## Testing & Proofing

Run fontbakery QA checks on all built fonts:

```bash
octalfont test --all
```

Run fontbakery QA checks on a single family by its ID:

```bash
octalfont test --family=titan
octalfont test --family=cuprum
octalfont test --family=mercury
```

Generate HTML proof documents via diffenator2:

```bash
octalfont proof --all
```

## Cleaning Build Artifacts

Remove fonts/ build outputs:

```bash
octalfont clean --all
```

Full reset - also removes logs/, QA reports, and Python caches:

```bash
octalfont clean --all --deep
```

> [!WARNING]
> `--deep` removes `logs/`, QA reports, and all Python caches (`__pycache__`,
> `.pytest_cache`, `.pyc`). UFO masters are **never** deleted - hand-edited
> `features.fea` files inside them are always preserved.

## Log Files

Build logs are written to `logs/` with a timestamp-prefixed directory per run.

> [!NOTE]
> You can specify a custom erase threshold for logs. By default, logs older than
> 7 days are deleted automatically on the next build.

## Updating Dependencies

```bash
octalfont update
```

Re-compiles both `requirements.txt` and `requirements-test.txt` from their `.in`
constraints and re-syncs the venv. Use this when you want to pull in newer
versions of the build tools, or after pulling changes to any `.in` file.

> [!TIP]
> `octalfont env --setup` already does this automatically. Run
> `octalfont update` only when you need to re-pin without recreating the venv.

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
- [Configuration](configuration.md)
