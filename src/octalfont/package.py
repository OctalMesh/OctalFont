"""Archive a built font repository for a GitHub Release (Google Fonts upstream layout)."""

from __future__ import annotations

import os
import time
import zipfile
from pathlib import Path

from .config import FontConfig

LEGAL_FILES = ("OFL.txt", "AUTHORS.txt", "CONTRIBUTORS.txt", "README.md")


def make_archive(cfg: FontConfig, out_dir: Path) -> Path:
    """Write ``<Family>-v<version>.zip`` and return its path.

    The archive is deterministic: entries are sorted and carry the timestamp
    ``SOURCE_DATE_EPOCH`` (or 1980-01-01), so rebuilding gives identical bytes.
    """

    fonts = cfg.root / "fonts"

    if not any(fonts.rglob("*.ttf")):
        raise FileNotFoundError(f"no built fonts in {fonts}; run `octalfont build` first")

    out_dir.mkdir(parents=True, exist_ok=True)

    stem = f"{cfg.file_stem}-v{cfg.version}"
    target = out_dir / f"{stem}.zip"

    epoch = int(os.environ.get("SOURCE_DATE_EPOCH", "315532800"))
    stamp = time.gmtime(max(epoch, 315532800))[:6]

    entries: list[tuple[Path, str]] = [(p, f"{stem}/fonts/{p.relative_to(fonts).as_posix()}")
                                       for p in sorted(fonts.rglob("*")) if p.is_file()]
    entries += [(cfg.root / name, f"{stem}/{name}") for name in LEGAL_FILES if (cfg.root / name).is_file()]

    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as zf:
        for path, arc in entries:
            info = zipfile.ZipInfo(arc, date_time=stamp)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            zf.writestr(info, path.read_bytes())

    return target
