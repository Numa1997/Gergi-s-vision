#!/usr/bin/env python3
"""Subset Noto Sans Math Regular into a small MathML-ready woff2 and embed it as CSS.

Source font: Noto Sans Math Regular, as served by the Google Fonts CSS2 API for
family=Noto+Sans+Math (https://fonts.gstatic.com/s/notosansmath/v19/7Aump_cpkSecTWaHRlH2hyV5UHkD.woff2).
Copyright 2022 Google LLC, SIL Open Font License 1.1 (https://openfontlicense.org).
The copy used here is stored at fonts/src/NotoSansMath-Regular.woff2 (override with --source).

Steps:
  1. Load the source font with fontTools.
  2. Subset it with the fontTools.subset API to the Unicode ranges in UNICODE_RANGES.
     Code points that Noto Sans Math lacks (U+02D9) are copied from Noto Sans
     Regular (SUPPLEMENT_FONT) after subsetting.
     The MATH table is kept (it is not in the default drop_tables list) and
     fontTools closes the glyph list over it, so glyph variants, glyph assemblies
     and italic-correction glyphs stay in the subset.
  3. Save fonts/math-subset.woff2 (flavor woff2) with all name records and
     layout features kept and hinting removed.
  4. Re-open the subset and check: MATH table with MathConstants, MathGlyphInfo
     and MathVariants; every glyph referenced by MathVariants is present; the
     required code points are in the cmap.
  5. Write fonts/math-embedded.css with one @font-face rule whose src is a
     base64 data: URI.

Requires fonttools and brotli:  pip install fonttools brotli

Usage:  python3 tools/build_math_font.py [--source PATH]
"""

import argparse
import base64
import sys
from pathlib import Path

from fontTools import subset
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont

FAMILY = "Hydraulics Math"

UNICODE_RANGES = [
    "U+0020-007E", "U+00A0-00FF", "U+0131", "U+02B0-02FF", "U+0300-036F",
    "U+0391-03C9", "U+03D1", "U+03D5",
    "U+03F0-03F1", "U+03F5", "U+2000-206F", "U+2100-214F", "U+2190-21FF",
    "U+2200-22FF", "U+2300-23FF", "U+25A0-25FF", "U+27E8-27EF", "U+2980-29FF",
    "U+2A00-2AFF", "U+1D400-1D7FF",
]

REQUIRED_CODEPOINTS = {
    0x1D465: "MATHEMATICAL ITALIC SMALL X",
    0x03C1: "GREEK SMALL LETTER RHO",
    0x222B: "INTEGRAL",
    0x2211: "N-ARY SUMMATION",
    0x221A: "SQUARE ROOT",
    0x0028: "LEFT PARENTHESIS",
    0x0029: "RIGHT PARENTHESIS",
    0x02D9: "DOT ABOVE",
    0x0307: "COMBINING DOT ABOVE",
}

ROOT = Path(__file__).resolve().parent.parent
FONTS_DIR = ROOT / "fonts"
DEFAULT_SOURCE = FONTS_DIR / "src" / "NotoSansMath-Regular.woff2"
# Noto Sans Regular (SIL OFL 1.1, Google Fonts), containing only U+02D9 (glyph "dotaccent").
# Noto Sans Math has no U+02D9, so that glyph is copied from here. Both fonts use 1000 units per em.
SUPPLEMENT_FONT = FONTS_DIR / "src" / "NotoSans-Regular-02D9.woff2"
SUPPLEMENT_CODEPOINTS = (0x02D9,)
SUBSET_PATH = FONTS_DIR / "math-subset.woff2"
EMBEDDED_CSS = FONTS_DIR / "math-embedded.css"


def parse_ranges(specs):
    """Expand 'U+0020-007E' or 'U+0131' specs into a set of code points."""
    codepoints = set()
    for spec in specs:
        start, _, end = spec[2:].partition("-")
        lo = int(start, 16)
        hi = int(end, 16) if end else lo
        codepoints.update(range(lo, hi + 1))
    return codepoints


def make_options():
    options = subset.Options()
    options.layout_features = ["*"]
    options.glyph_names = False
    options.notdef_outline = True
    options.name_IDs = ["*"]
    options.hinting = False  # drops cvt/fpgm/prep; about 54 KB smaller
    options.flavor = "woff2"
    return options


def add_supplement_glyphs(font, supplement_path, codepoints):
    """Copy glyphs for code points the subset lacks from a supplement font.

    Returns a list of (code point, glyph name, advance) for each glyph added.
    """
    cmap = font.getBestCmap()
    wanted = [cp for cp in codepoints if cp not in cmap]
    if not wanted:
        return []
    donor = TTFont(str(supplement_path))
    if donor["head"].unitsPerEm != font["head"].unitsPerEm:
        raise SystemExit("supplement font and source font have different unitsPerEm")
    donor_cmap = donor.getBestCmap()
    donor_glyphs = donor.getGlyphSet()
    order = font.getGlyphOrder()
    added = []
    for cp in wanted:
        if cp not in donor_cmap:
            raise SystemExit(f"U+{cp:04X} is not in the supplement font either")
        donor_name = donor_cmap[cp]
        name = f"uni{cp:04X}"
        if name in order:
            raise SystemExit(f"glyph name {name} already exists in the subset")
        pen = TTGlyphPen(donor_glyphs)
        donor_glyphs[donor_name].draw(pen)
        advance, lsb = donor["hmtx"][donor_name]
        font["glyf"].glyphs[name] = pen.glyph()
        font["hmtx"].metrics[name] = (advance, lsb)
        order.append(name)
        for table in font["cmap"].tables:
            if table.isUnicode():
                table.cmap[cp] = name
        added.append((cp, name, advance))
    font.setGlyphOrder(order)
    font["maxp"].numGlyphs = len(order)
    return added


def build_subset(source, out_path):
    font = TTFont(str(source))
    subsetter = subset.Subsetter(options=make_options())
    subsetter.populate(unicodes=parse_ranges(UNICODE_RANGES))
    subsetter.subset(font)
    added = add_supplement_glyphs(font, SUPPLEMENT_FONT, SUPPLEMENT_CODEPOINTS)
    font.flavor = "woff2"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    font.save(str(out_path))
    return added


def math_glyph_refs(math):
    """Collect every glyph name that MathVariants refers to (variants and assemblies)."""
    refs = set()
    mv = math.MathVariants
    if mv is None:
        return refs
    pairs = (
        (mv.VertGlyphCoverage, mv.VertGlyphConstruction),
        (mv.HorizGlyphCoverage, mv.HorizGlyphConstruction),
    )
    for coverage, constructions in pairs:
        if coverage is None or not constructions:
            continue
        refs.update(coverage.glyphs)
        for construction in constructions:
            if construction is None:
                continue
            for record in construction.MathGlyphVariantRecord or []:
                refs.add(record.VariantGlyph)
            if construction.GlyphAssembly is not None:
                for part in construction.GlyphAssembly.PartRecords or []:
                    refs.add(part.glyph)
    return refs


def verify_subset(path):
    """Re-open the subset and raise SystemExit on any missing requirement."""
    font = TTFont(str(path))
    problems = []

    if "MATH" not in font:
        problems.append("MATH table is missing")
    else:
        math = font["MATH"].table
        for attr in ("MathConstants", "MathGlyphInfo", "MathVariants"):
            if getattr(math, attr, None) is None:
                problems.append(f"MATH.{attr} is missing")
        glyph_order = set(font.getGlyphOrder())
        dangling = sorted(math_glyph_refs(math) - glyph_order)
        if dangling:
            problems.append(f"MathVariants reference {len(dangling)} glyphs not in the subset")

    cmap = font.getBestCmap()
    for cp, name in REQUIRED_CODEPOINTS.items():
        if cp not in cmap:
            problems.append(f"U+{cp:04X} {name} is not in the cmap")
    dangling_cmap = sorted(set(cmap.values()) - set(font.getGlyphOrder()))
    if dangling_cmap:
        problems.append(f"cmap points at {len(dangling_cmap)} glyphs not in the glyph order")

    if problems:
        raise SystemExit("verification failed:\n  " + "\n  ".join(problems))

    return len(font.getGlyphOrder())


def write_css(woff2_path, css_path):
    data = base64.b64encode(woff2_path.read_bytes()).decode("ascii")
    css = (
        "/* Noto Sans Math Regular subset. Copyright 2022 Google LLC, SIL Open Font License 1.1. */\n"
        "@font-face {\n"
        f'  font-family: "{FAMILY}";\n'
        "  font-style: normal;\n"
        "  font-weight: 400;\n"
        "  font-display: swap;\n"
        f"  src: url(data:font/woff2;base64,{data}) format('woff2');\n"
        "}\n"
    )
    css_path.write_text(css, encoding="ascii")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Build the Hydraulics Math subset font and its embedded CSS.")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE,
                        help="path to the full Noto Sans Math Regular font (woff2, ttf or otf)")
    args = parser.parse_args(argv)

    if not args.source.is_file():
        parser.error(f"source font not found: {args.source} (see the module docstring for the download URL)")

    added = build_subset(args.source, SUBSET_PATH)
    glyph_count = verify_subset(SUBSET_PATH)
    write_css(SUBSET_PATH, EMBEDDED_CSS)

    codepoints = len(parse_ranges(UNICODE_RANGES))
    print(f"source:       {args.source} ({args.source.stat().st_size} bytes)")
    for cp, name, advance in added:
        print(f"supplement:   U+{cp:04X} copied from {SUPPLEMENT_FONT.name} as {name} (advance {advance})")
    print(f"codepoints:   {codepoints} requested by the ranges")
    print(f"glyphs:       {glyph_count}")
    print(f"subset:       {SUBSET_PATH} ({SUBSET_PATH.stat().st_size} bytes)")
    print(f"css:          {EMBEDDED_CSS} ({EMBEDDED_CSS.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
