"""Command-line interface for the svg_to_ufo pipeline.

Typical usage::

    python -m svg_to_ufo sources/OctalFont-Titan
    python -m svg_to_ufo sources/OctalFont-Titan --weight Regular
    python -m svg_to_ufo sources/OctalFont-Titan --dry-run
"""

from __future__ import annotations

import argparse
import sys
import traceback
from collections.abc import Sequence
from pathlib import Path

from svg_to_ufo.config import KNOWN_WEIGHTS
from svg_to_ufo.metrics import load_metrics
from svg_to_ufo.ufo.builder import build_ufo
from svg_to_ufo.ufo.designspace import build_designspace


def _build_parser() -> argparse.ArgumentParser:
    """Return the configured argument parser for svg_to_ufo."""

    parser = argparse.ArgumentParser(
        prog="svg_to_ufo",
        description=(
            "Convert per-glyph SVG files into a UFO master + DesignSpace "
            "suitable for fontmake / gftools builder."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "family_dir",
        type=Path,
        help=(
            "Path to the family source directory "
            "(e.g. sources/OctalFont-Titan)."
        ),
    )
    parser.add_argument(
        "--weight",
        default=None,
        metavar="NAME",
        help=(
            "Weight name for the UFO master (e.g. Regular, Light, Bold). "
            "Omit to build all per-weight subdirectories found under svg/ "
            "automatically (same as --all-weights)."
        ),
    )
    parser.add_argument(
        "--all-weights",
        action="store_true",
        help="Build UFO masters for every weight subdir found under svg/.",
    )
    parser.add_argument(
        "--no-designspace",
        action="store_true",
        help="Skip .designspace generation entirely.",
    )
    parser.add_argument(
        "--force-designspace",
        action="store_true",
        help="Overwrite the .designspace file even if it already exists.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be done without writing any files.",
    )

    return parser


def _resolve_weights(
    family_dir: Path,
    weight_arg: str | None,
    all_weights: bool,
) -> list[str]:
    """Return the ordered list of weight names to build.

    Priority:
        1. ``--weight NAME``: single explicit weight.
        2. ``--all-weights``: every canonical subdir found under ``svg/``.
        3. Auto-detect: any ``svg/<Weight>/`` directory matching a known name.
        4. Fallback: ``["Regular"]``.

    Args:
        family_dir: Absolute path to the family source directory.
        weight_arg: Value of the ``--weight`` flag, or None when not given.
        all_weights: Whether ``--all-weights`` was passed.

    Returns:
        An ordered list of weight name strings to build.
    """

    if weight_arg:
        return [weight_arg]

    svg_base = family_dir / "svg"
    detected: list[str] = []

    if svg_base.is_dir():
        detected = sorted(
            subdir.name for subdir in svg_base.iterdir()
            if subdir.is_dir() and subdir.name in KNOWN_WEIGHTS
        )

    if all_weights or detected:
        return detected or ["Regular"]

    return ["Regular"]


def main(argv: Sequence[str] | None = None) -> int:
    """Run the svg_to_ufo pipeline.

    Args:
        argv: Argument list. Defaults to sys.argv[1:] when None.

    Returns:
        0 on success, 1 when one or more weights failed.
    """

    parsed_args = _build_parser().parse_args(argv)

    family_dir: Path = parsed_args.family_dir.resolve()
    if not family_dir.is_dir():
        print(
            f"[ERROR] Family directory not found: {family_dir}",
            file=sys.stderr,
        )

        return 1

    print(
        f"\n[svg_to_ufo] Family: {family_dir.name}"
        + ("  (DRY RUN - no files written)" if parsed_args.dry_run else "")
        + "\n"
    )

    metrics = load_metrics(family_dir)
    metrics.setdefault("family_name", family_dir.name)

    weights_to_build = _resolve_weights(
        family_dir, parsed_args.weight, parsed_args.all_weights
    )

    # Build each UFO master.
    built_ufos: dict[str, Path] = {}
    errors = 0

    for weight_name in weights_to_build:
        print(f"  -- Weight: {weight_name}")

        try:
            ufo_path = build_ufo(
                family_dir=family_dir,
                weight_name=weight_name,
                metrics=metrics,
                dry_run=parsed_args.dry_run,
            )
            built_ufos[weight_name] = ufo_path
        except FileNotFoundError as exc:
            print(f"  [ERROR] {exc}", file=sys.stderr)
            errors += 1
        except Exception as exc:
            print(
                f"  [ERROR] Unexpected error building {weight_name}: {exc}",
                file=sys.stderr,
            )
            traceback.print_exc()
            errors += 1

    # Update the DesignSpace once, with all successfully built weights.
    if built_ufos and not parsed_args.no_designspace:
        try:
            build_designspace(
                family_dir=family_dir,
                ufo_paths=built_ufos,
                metrics=metrics,
                dry_run=parsed_args.dry_run,
                force=parsed_args.force_designspace,
            )
        except Exception as exc:
            print(
                f"  [ERROR] DesignSpace generation failed: {exc}",
                file=sys.stderr,
            )
            traceback.print_exc()
            errors += 1

    if not parsed_args.dry_run:
        print("\n[svg_to_ufo] Done.\n")

    return 0 if errors == 0 else 1
