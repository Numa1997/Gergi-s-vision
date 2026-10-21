#!/usr/bin/env python3
"""Strip the document wrapper so a page can be published as an Artifact (the host adds its own skeleton).
Usage: python3 tools/make_artifact.py page.html out.html"""
import re, sys
src = open(sys.argv[1]).read()
for pat in [r'<!doctype html>\n', r'<html lang="en">\n', r'<head>\n', r'</head>\n', r'<body>\n', r'</body>\n', r'</html>\n?',
            r'<meta charset="utf-8">\n', r'<meta name="viewport"[^>]*>\n']:
    src = re.sub(pat, '', src, count=1)
open(sys.argv[2], 'w').write(src)
print('wrote', sys.argv[2], len(src), 'bytes')
