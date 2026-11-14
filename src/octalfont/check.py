"""Project checks against Google Fonts requirements (fast, offline)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .config import FontConfig
from .glyphnames import glyph_name_for, glyphset_unicodes


@dataclass
class Finding:
    level: str  # PASS | WARN | FAIL
    message: str

    def __str__(self) -> str:
        return f"[{self.level}] {self.message}"


def _has_entries(path: Path) -> bool:
    """True if a name list has at least one line that is not blank or a comment."""
    return any(line.strip() and not line.lstrip().startswith("#")
               for line in path.read_text(encoding="utf-8").splitlines())


def check_legal(cfg: FontConfig) -> list[Finding]:
    out: list[Finding] = []
    ofl = cfg.root / "OFL.txt"

    if not ofl.is_file():
        out.append(Finding("WARN", "OFL.txt is missing"))
    else:
        first = ofl.read_text(encoding="utf-8").splitlines()[0].strip()

        if first != cfg.copyright:
            out.append(Finding("WARN", f"OFL.txt line 1 must equal the copyright string:\n    {cfg.copyright}"))

        text = ofl.read_text(encoding="utf-8")

        if "Reserved Font Name" in text.split("PREAMBLE", 1)[0]:
            out.append(Finding("WARN", "OFL.txt declares a Reserved Font Name; GF does not accept RFNs"))

    if not (cfg.root / "AUTHORS.txt").is_file():
        out.append(Finding("WARN", "AUTHORS.txt is missing"))

    contributors = cfg.root / "CONTRIBUTORS.txt"

    if contributors.is_file() and not _has_entries(contributors):
        out.append(Finding("WARN", "CONTRIBUTORS.txt has no contributors; delete it until there are some"))

    if not (cfg.root / "requirements.txt").is_file():
        out.append(Finding("WARN", "requirements.txt is missing"))

    return out or [Finding("PASS", "legal files present and consistent")]


def check_metrics(cfg: FontConfig, stack_top: float | None, win: tuple[int, int],
                  deepest: float, tallest: float) -> list[Finding]:
    m, out = cfg.metrics, []
    total = (m.ascender - m.descender) / m.upm

    out.append(Finding("PASS" if 1.2 <= total <= 1.3 else "WARN",
                       f"ascender+|descender| = {total:.0%} of UPM (GF recommends 120-130%)"))

    centred = m.ascender - m.cap_height == -m.descender

    out.append(Finding("PASS" if centred else "WARN",
                       f"caps centred in the line: ascender-cap={m.ascender - m.cap_height}, |descender|={-m.descender}"))

    if m.ascender < tallest:
        out.append(Finding("WARN", f"tallest glyph reaches {tallest:.0f}, above ascender {m.ascender}: "
                                   "accents will crowd the line (Font Bakery's own check may still pass)"))
    else:
        out.append(Finding("PASS", f"ascender {m.ascender} clears the tallest glyph ({tallest:.0f})"))

    if stack_top is None:
        out.append(Finding("WARN", "cannot estimate U+1EAE (needs A, breve and acute marks)"))
    elif m.ascender < stack_top:
        out.append(Finding("WARN", f"U+1EAE (Vietnamese) would reach {stack_top:.0f}, above ascender {m.ascender}; "
                                   "metrics cannot change after release, so decide on Vietnamese before 1.000"))
    else:
        out.append(Finding("PASS", f"ascender {m.ascender} covers U+1EAE (height {stack_top:.0f})"))

    if -m.descender < -deepest:
        out.append(Finding("WARN", f"descender {m.descender} is shallower than the deepest glyph ({deepest:.0f})"))

    out.append(Finding("PASS", f"win metrics (family-wide): ascent={win[0]}, descent={abs(win[1])}"))

    return out


def check_coverage(font, cfg: FontConfig) -> tuple[list[Finding], dict[str, list[str]]]:
    have = {u for g in font for u in g.unicodes}
    out, missing = [], {}

    for gs, kind in [(g, "required") for g in cfg.required_glyphsets] + [
            (g, "optional") for g in cfg.optional_glyphsets]:
        want = set(glyphset_unicodes(gs))
        gone = sorted(want - have)
        missing[gs] = [glyph_name_for(u, gs) for u in gone]
        level = "PASS" if not gone else ("FAIL" if kind == "required" else "WARN")

        out.append(Finding(level, f"{gs} ({kind}): {len(want) - len(gone)}/{len(want)} glyphs"
                                  + (f", {len(gone)} missing" if gone else "")))

    return out, missing
