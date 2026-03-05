"""SVG filename to (glyph_name, unicode_codepoint) mapping."""

from __future__ import annotations

import unicodedata

# Maps SVG filename stems to (glyph_name, unicode_codepoint).
# Single ASCII letters and printable chars resolve automatically; the table
# below covers numerals, punctuation, and names that don't equal the char.
FILENAME_MAP: dict[str, tuple[str, int]] = {
    # <editor-fold desc="Numerals" defaultstate="collapsed">
    "0": ("zero",  0x0030),
    "1": ("one",   0x0031),
    "2": ("two",   0x0032),
    "3": ("three", 0x0033),
    "4": ("four",  0x0034),
    "5": ("five",  0x0035),
    "6": ("six",   0x0036),
    "7": ("seven", 0x0037),
    "8": ("eight", 0x0038),
    "9": ("nine",  0x0039),
    # </editor-fold>
    # <editor-fold desc="Punctuation" defaultstate="collapsed">
    "period":       ("period",       0x002E),
    "comma":        ("comma",        0x002C),
    "colon":        ("colon",        0x003A),
    "semicolon":    ("semicolon",    0x003B),
    "exclam":       ("exclam",       0x0021),
    "question":     ("question",     0x003F),
    "hyphen":       ("hyphen",       0x002D),
    "underscore":   ("underscore",   0x005F),
    "slash":        ("slash",        0x002F),
    "backslash":    ("backslash",    0x005C),
    "at":           ("at",           0x0040),
    "ampersand":    ("ampersand",    0x0026),
    "parenleft":    ("parenleft",    0x0028),
    "parenright":   ("parenright",   0x0029),
    "bracketleft":  ("bracketleft",  0x005B),
    "bracketright": ("bracketright", 0x005D),
    "braceleft":    ("braceleft",    0x007B),
    "braceright":   ("braceright",   0x007D),
    "quotedbl":     ("quotedbl",     0x0022),
    "quotesingle":  ("quotesingle",  0x0027),
    "grave":        ("grave",        0x0060),
    "asterisk":     ("asterisk",     0x002A),
    "plus":         ("plus",         0x002B),
    "equal":        ("equal",        0x003D),
    "less":         ("less",         0x003C),
    "greater":      ("greater",      0x003E),
    "percent":      ("percent",      0x0025),
    "numbersign":   ("numbersign",   0x0023),
    "dollar":       ("dollar",       0x0024),
    "caret":        ("asciicircum",  0x005E),
    "tilde":        ("asciitilde",   0x007E),
    "pipe":         ("bar",          0x007C),
    "space":        ("space",        0x0020),
    # </editor-fold>
}


def stem_to_glyph(stem: str) -> tuple[str, int | None]:
    """Return (glyph_name, unicode_or_None) for an SVG filename stem.

    Lookup order:
        1. FILENAME_MAP: explicit table for numerals and named punctuation.
        2. Single printable ASCII character: letter name used directly;
           other chars derive their name from the Unicode character name.
        3. Unknown or ligature stem: returned as-is with no Unicode assignment.

    Args:
        stem: Filename stem without extension, e.g. ``A`` or ``exclam``.

    Returns:
        A tuple of (glyph_name, unicode_codepoint). unicode_codepoint is
        None when no Unicode assignment is known.
    """

    if stem in FILENAME_MAP:
        return FILENAME_MAP[stem]

    # Single printable ASCII character (A-Z, a-z, etc.).
    if len(stem) == 1 and stem.isprintable():
        unicode_codepoint = ord(stem)

        if stem.isalpha():
            return stem, unicode_codepoint

        try:
            unicode_char_name = unicodedata.name(stem).lower().replace(" ", "")
        except ValueError:
            unicode_char_name = stem

        return unicode_char_name, unicode_codepoint

    # Unknown / multi-char / ligature - no Unicode assignment.
    return stem, None
