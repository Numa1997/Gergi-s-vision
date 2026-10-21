#!/usr/bin/env python3
"""Build self-hosted woff2 copies of the Google Fonts used by the static page.

Standard library only. Steps:
  1. Fetch the Google Fonts CSS2 stylesheet with a desktop Chrome User-Agent,
     so Google serves woff2 files.
  2. Parse every @font-face block and keep only the "latin" and "greek" subsets.
  3. Merge blocks that share the same src URL, family, style and subset into one
     group. A group whose blocks cover several weights gets a range font-weight
     ("MIN MAX") and one file named <family>-<MIN>-<MAX>-<style>-<subset>.woff2.
     Each distinct woff2 file is downloaded and written once.
  4. Remove stale ibm-plex-* and instrument-serif-* *.woff2 files in fonts/ that this run
     did not produce. Other files in fonts/ are not touched.
  5. Write fonts/fonts-embedded.css (base64 data: URIs) and
     fonts/fonts-linked.css (relative file URLs), one rule per group.
  6. Print a summary table.

Network goes through HTTPS_PROXY as configured in the environment. TLS
verification is never disabled; if the default CA store rejects the proxy
certificate, the CA bundle at CA_BUNDLE is used instead.

Usage:  python3 tools/build_fonts.py
"""

import base64
import re
import ssl
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

CSS_URL = (
    "https://fonts.googleapis.com/css2?"
    "family=IBM+Plex+Mono:wght@400;500"
    "&family=IBM+Plex+Sans:ital,wght@0,400;0,500;0,600;1,400"
    "&family=Instrument+Serif:ital@0;1"
    "&display=swap"
)
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
KEEP_SUBSETS = ("latin", "greek")
CA_BUNDLE = "/root/.ccr/ca-bundle.crt"

ROOT = Path(__file__).resolve().parent.parent
FONTS_DIR = ROOT / "fonts"
EMBEDDED_CSS = FONTS_DIR / "fonts-embedded.css"
LINKED_CSS = FONTS_DIR / "fonts-linked.css"

# A subset comment such as "/* latin */" immediately followed by an @font-face block.
BLOCK_RE = re.compile(r"/\*\s*(?P<subset>[^*/]+?)\s*\*/\s*@font-face\s*\{(?P<body>[^}]*)\}")
WOFF2_MAGIC = b"wOF2"
# Output names are slugs of the Google family names (see Group.filename). Only files with these
# prefixes belong to this script; other files in fonts/ (for example math-subset.woff2) are left alone.
OWNED_PREFIXES = ("ibm-plex-", "instrument-serif-")


@dataclass
class Face:
    """One @font-face block as published by Google."""
    family: str
    weight: int
    style: str
    subset: str
    unicode_range: str
    url: str


@dataclass
class Group:
    """One output font file: all blocks sharing src URL, family, style and subset."""
    family: str
    style: str
    subset: str
    url: str
    unicode_range: str
    weights: list[int] = field(default_factory=list)

    @property
    def weight_label(self) -> str:
        lo, hi = min(self.weights), max(self.weights)
        return str(lo) if lo == hi else f"{lo}-{hi}"

    @property
    def css_weight(self) -> str:
        lo, hi = min(self.weights), max(self.weights)
        return str(lo) if lo == hi else f"{lo} {hi}"

    @property
    def filename(self) -> str:
        slug = self.family.lower().replace(" ", "-")
        return f"{slug}-{self.weight_label}-{self.style}-{self.subset}.woff2"


_tls_context = None  # replaced by the CA-bundle context only if the default store fails


def _is_tls_error(exc: Exception) -> bool:
    reason = getattr(exc, "reason", None)
    return isinstance(exc, ssl.SSLError) or isinstance(reason, ssl.SSLError)


def fetch(url: str) -> bytes:
    """GET a URL with urllib. TLS verification stays enabled."""
    global _tls_context
    while True:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=60, context=_tls_context) as resp:
                return resp.read()
        except (urllib.error.URLError, ssl.SSLError) as exc:
            if _tls_context is not None or not _is_tls_error(exc) or not Path(CA_BUNDLE).is_file():
                raise
            print(f"TLS verification failed ({exc}); retrying with CA bundle {CA_BUNDLE}",
                  file=sys.stderr)
            _tls_context = ssl.create_default_context(cafile=CA_BUNDLE)


def _prop(body: str, name: str) -> str:
    m = re.search(rf"^\s*{re.escape(name)}\s*:\s*(.+?)\s*;\s*$", body, re.MULTILINE)
    if m is None:
        raise ValueError(f"@font-face block has no '{name}' property")
    return m.group(1)


def parse_faces(css: str) -> list[Face]:
    total = css.count("@font-face")
    faces = []
    for m in BLOCK_RE.finditer(css):
        body = m.group("body")
        src = _prop(body, "src")
        url_m = re.search(r"url\(\s*['\"]?([^'\")\s]+)['\"]?\s*\)", src)
        if url_m is None or re.search(r"format\(\s*['\"]woff2['\"]\s*\)", src) is None:
            raise ValueError(f"@font-face src is not a woff2 url: {src}")
        faces.append(Face(
            family=_prop(body, "font-family").strip("'\""),
            weight=int(_prop(body, "font-weight")),
            style=_prop(body, "font-style"),
            subset=m.group("subset"),
            unicode_range=_prop(body, "unicode-range"),
            url=url_m.group(1),
        ))
    if len(faces) != total:
        raise RuntimeError(f"parsed {len(faces)} of {total} @font-face blocks; "
                           "a block is missing its subset comment")
    return faces


def merge_faces(faces: list[Face]) -> list[Group]:
    """Group blocks by (src URL, family, style, subset); collect their weights."""
    groups: dict[tuple, Group] = {}
    for f in faces:
        key = (f.url, f.family, f.style, f.subset)
        if key not in groups:
            groups[key] = Group(f.family, f.style, f.subset, f.url, f.unicode_range)
        g = groups[key]
        if g.unicode_range != f.unicode_range:
            raise RuntimeError(f"blocks sharing {f.url} have different unicode-range values")
        if f.weight not in g.weights:
            g.weights.append(f.weight)
    for g in groups.values():
        g.weights.sort()
    return list(groups.values())


def download(url: str, label: str) -> bytes:
    data = fetch(url)
    if data[:4] != WOFF2_MAGIC:
        raise RuntimeError(f"{label}: downloaded file is not woff2")
    return data


def css_rule(g: Group, src: str) -> str:
    return (
        f"/* {g.family}, weight {g.weight_label}, {g.style}, subset {g.subset} */\n"
        "@font-face {\n"
        f"  font-family: '{g.family}';\n"
        f"  font-style: {g.style};\n"
        f"  font-weight: {g.css_weight};\n"
        "  font-display: swap;\n"
        f"  src: {src};\n"
        f"  unicode-range: {g.unicode_range};\n"
        "}\n"
    )


def print_table(items: list[tuple[Group, bytes]]) -> None:
    fam_w = max([len("Family")] + [len(g.family) for g, _ in items])
    print(f"{'Family':<{fam_w}}  {'Weight':>7}  {'Style':<7}  {'Subset':<8}  {'woff2 bytes':>11}")
    print("-" * (fam_w + 45))
    for g, data in items:
        print(f"{g.family:<{fam_w}}  {g.weight_label:>7}  {g.style:<7}  {g.subset:<8}  {len(data):>11}")


def main() -> None:
    FONTS_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Fetching {CSS_URL}")
    css = fetch(CSS_URL).decode("utf-8")
    faces = parse_faces(css)
    kept = [f for f in faces if f.subset in KEEP_SUBSETS]
    print(f"Parsed {len(faces)} @font-face blocks; keeping {len(kept)} "
          f"(subsets: {', '.join(KEEP_SUBSETS)}).")

    groups = merge_faces(kept)
    print(f"Merged into {len(groups)} font files / CSS rules.")

    names = [g.filename for g in groups]
    duplicates = sorted({n for n in names if names.count(n) > 1})
    if duplicates:
        raise RuntimeError(f"duplicate output file names: {duplicates}")

    # Download each distinct source URL once; write one file per group.
    data_by_url: dict[str, bytes] = {}
    items: list[tuple[Group, bytes]] = []
    for g in groups:
        if g.url not in data_by_url:
            data_by_url[g.url] = download(g.url, g.filename)
        data = data_by_url[g.url]
        (FONTS_DIR / g.filename).write_bytes(data)
        items.append((g, data))

    for stale in sorted(FONTS_DIR.glob("*.woff2")):
        if stale.name.startswith(OWNED_PREFIXES) and stale.name not in set(names):
            stale.unlink()
            print(f"Removed stale {stale.name}")

    embedded_rules = []
    linked_rules = []
    for g, data in items:
        b64 = base64.b64encode(data).decode("ascii")
        embedded_rules.append(css_rule(g, f"url(data:font/woff2;base64,{b64}) format('woff2')"))
        linked_rules.append(css_rule(g, f"url('{g.filename}') format('woff2')"))
    embedded_css = "\n".join(embedded_rules)
    linked_css = "\n".join(linked_rules)
    if embedded_css.count("@font-face {") != len(items) or linked_css.count("@font-face {") != len(items):
        raise RuntimeError("generated CSS rule count does not match font group count")
    EMBEDDED_CSS.write_text(embedded_css, encoding="utf-8")
    LINKED_CSS.write_text(linked_css, encoding="utf-8")

    print()
    print_table(items)
    print()
    total = sum(len(d) for d in data_by_url.values())
    print(f"Total woff2 bytes: {total}  ({len(data_by_url)} files, {len(items)} CSS rules)")
    print(f"fonts-embedded.css bytes: {EMBEDDED_CSS.stat().st_size}")
    print(f"fonts-linked.css bytes: {LINKED_CSS.stat().st_size}")
    print(f"Output directory: {FONTS_DIR}")


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, ValueError, urllib.error.URLError) as exc:
        sys.exit(f"build_fonts: error: {exc}")
