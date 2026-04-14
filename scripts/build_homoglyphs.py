#!/usr/bin/env python3
"""Build extended homoglyph map from Unicode Confusables data.

Downloads the Unicode Consortium's confusables.txt dataset and generates
a Python module containing EXTENDED_HOMOGLYPH_MAP — a dict mapping confusable
characters to their ASCII-printable canonical equivalents.

Usage:
    python scripts/build_homoglyphs.py

Output:
    stenography/data/homoglyphs_generated.py
"""

import sys
import unicodedata
import urllib.error
import urllib.request
from pathlib import Path

CONFUSABLES_URL = "https://www.unicode.org/Public/security/latest/confusables.txt"
OUTPUT_PATH = Path(__file__).parent.parent / "stenography" / "data" / "homoglyphs_generated.py"

# ASCII printable range (space through tilde, i.e. 0x20–0x7E)
ASCII_PRINTABLE = set(chr(i) for i in range(0x20, 0x7F))


def _script_name(char: str) -> str:
    """Derive a human-readable script name from the Unicode character name."""
    try:
        name = unicodedata.name(char, "")
    except (ValueError, TypeError):
        return "Other"

    prefixes = [
        ("CYRILLIC", "Cyrillic"),
        ("GREEK", "Greek"),
        ("ARMENIAN", "Armenian"),
        ("ARABIC", "Arabic"),
        ("HEBREW", "Hebrew"),
        ("GEORGIAN", "Georgian"),
        ("CHEROKEE", "Cherokee"),
        ("THAI", "Thai"),
        ("DEVANAGARI", "Devanagari"),
        ("BENGALI", "Bengali"),
        ("GUJARATI", "Gujarati"),
        ("GURMUKHI", "Gurmukhi"),
        ("KANNADA", "Kannada"),
        ("MALAYALAM", "Malayalam"),
        ("MYANMAR", "Myanmar"),
        ("ORIYA", "Oriya"),
        ("SINHALA", "Sinhala"),
        ("TAMIL", "Tamil"),
        ("TELUGU", "Telugu"),
        ("TIBETAN", "Tibetan"),
        ("FULLWIDTH", "Fullwidth"),
        ("LATIN", "Latin-Ext"),
        ("DIGIT", "Latin"),
    ]
    for prefix, label in prefixes:
        if name.startswith(prefix):
            return label
    return "Other"


def parse_confusables(text: str) -> dict[str, tuple[str, str]]:
    """Parse confusables.txt and return {source_char: (target_char, script)} dict.

    Only keeps entries where:
    - The source is a single Unicode character.
    - The target resolves to a single ASCII-printable character.
    """
    mapping: dict[str, tuple[str, str]] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        # Skip blank lines and comments
        if not line or line.startswith("#"):
            continue

        parts = line.split(";")
        if len(parts) < 2:
            continue

        src_hex = parts[0].strip()
        tgt_hex = parts[1].strip()

        # Only handle single-codepoint sources
        src_codepoints = src_hex.split()
        tgt_codepoints = tgt_hex.split()

        if len(src_codepoints) != 1 or len(tgt_codepoints) != 1:
            continue

        try:
            src_char = chr(int(src_codepoints[0], 16))
            tgt_char = chr(int(tgt_codepoints[0], 16))
        except (ValueError, OverflowError):
            continue

        # Skip if source is itself ASCII (not a confusable threat)
        if src_char in ASCII_PRINTABLE:
            continue

        # Only keep entries where target is ASCII printable (dangerous confusables)
        if tgt_char not in ASCII_PRINTABLE:
            continue

        # Prefer entries with a recognisable script label over "Other"
        script = _script_name(src_char)
        mapping[src_char] = (tgt_char, script)

    return mapping


def render_module(mapping: dict[str, tuple[str, str]]) -> str:
    """Render the Python module source for homoglyphs_generated.py."""
    lines = [
        '"""Auto-generated extended homoglyph map from Unicode Confusables data.',
        "",
        "Source: https://www.unicode.org/Public/security/latest/confusables.txt",
        "",
        "DO NOT EDIT — regenerate with:  python scripts/build_homoglyphs.py",
        '"""',
        "from __future__ import annotations",
        "",
        "# Maps confusable Unicode char -> (ascii_equivalent, script_name)",
        "EXTENDED_HOMOGLYPH_MAP: dict[str, tuple[str, str]] = {",
    ]

    for src_char, (tgt_char, script) in sorted(mapping.items(), key=lambda kv: ord(kv[0])):
        src_u = f"U+{ord(src_char):04X}"
        tgt_u = f"U+{ord(tgt_char):04X}"
        try:
            src_name = unicodedata.name(src_char, src_u)
        except (ValueError, TypeError):
            src_name = src_u
        entry = (
            f'    "\\u{ord(src_char):04X}": ("{tgt_char}", "{script}"),  '
            f"# {src_name} -> {tgt_u}"
        )
        lines.append(entry)

    lines += ["}", ""]
    return "\n".join(lines)


def main() -> None:
    print(f"Downloading {CONFUSABLES_URL} …", flush=True)
    try:
        with urllib.request.urlopen(CONFUSABLES_URL, timeout=30) as resp:
            raw = resp.read().decode("utf-8-sig")
    except (urllib.error.URLError, OSError) as exc:
        print(f"ERROR: could not fetch confusables.txt: {exc}", file=sys.stderr)
        sys.exit(1)

    mapping = parse_confusables(raw)
    print(f"Parsed {len(mapping)} single-char ASCII-target confusable entries.")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    module_src = render_module(mapping)
    OUTPUT_PATH.write_text(module_src, encoding="utf-8")
    print(f"Written to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
