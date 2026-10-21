#!/usr/bin/env python3
"""Prepare a page for publishing as an Artifact.

The host adds its own document skeleton, so the doctype, html, head and body wrappers are stripped.
Links between the three pages (hydraulic.html, hydraulic_control.html, hydraulic_theory.html) are rewritten
to their published Artifact URLs, listed in tools/artifact_urls.json.

Usage: python3 tools/make_artifact.py page.html out.html
"""
import json
import pathlib
import re
import sys

src = open(sys.argv[1]).read()
for pat in [r'<!doctype html>\n', r'<html lang="en">\n', r'<head>\n', r'</head>\n', r'<body>\n', r'</body>\n', r'</html>\n?',
            r'<meta charset="utf-8">\n', r'<meta name="viewport"[^>]*>\n']:
    src = re.sub(pat, '', src, count=1)
urls_file = pathlib.Path(__file__).with_name('artifact_urls.json')
urls = json.loads(urls_file.read_text()) if urls_file.exists() else {}
for page, url in urls.items():
    if url:
        src = src.replace(f'href="{page}"', f'href="{url}" target="_blank" rel="noopener"')
open(sys.argv[2], 'w').write(src)
print('wrote', sys.argv[2], len(src), 'bytes')
