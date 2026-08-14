"""Font metrics loader from metrics.yaml."""

from __future__ import annotations

from pathlib import Path

try:
    import yaml
except ImportError:
    raise SystemExit("[svg_to_ufo] Missing dependency: pyyaml\nRun: octalfont env --setup")


def load_metrics(family_dir: Path) -> dict:
    """Load metrics.yaml from family_dir and return it as a plain dict.

    Falls back to an empty dict when the file is absent, letting the
    pipeline continue with sensible defaults.

    Args:
        family_dir: Absolute path to the family source directory,
            e.g. ``sources/OctalFont-Titan``.

    Returns:
        A dict of font metric keys, or an empty dict when the file
        is absent.
    """

    metrics_file = family_dir / "metrics.yaml"

    if not metrics_file.exists():
        print("  [INFO] metrics.yaml not found, using defaults.")

        return {}
    with metrics_file.open(encoding="utf-8") as file_handle:
        return yaml.safe_load(file_handle) or {}
