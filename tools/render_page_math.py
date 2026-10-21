#!/usr/bin/env python3
"""Typeset the equation blocks of hydraulic.html and hydraulic_control.html with KaTeX, in place.

The first run replaces each plain-text <div class="eq"> with the LaTeX of tools/page_equations.py;
later runs re-render from each block's data-tex attribute, so the script can be run any number of
times. The KaTeX stylesheet, with the fonts it needs embedded, goes between /*KATEX-BEGIN*/ and
/*KATEX-END*/ in the page's first <style>.

Usage: (cd tools && npm install) once, then python3 tools/render_page_math.py
"""
import base64
import html
import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOLS = ROOT / 'tools'
KATEX = TOOLS / 'node_modules' / 'katex' / 'dist'
sys.path.insert(0, str(TOOLS))
from page_equations import CONTROL, IDEAL   # noqa: E402

PAGES = {'hydraulic_control.html': CONTROL, 'hydraulic.html': IDEAL}
BLOCK = re.compile(r'<div class="eq tex" data-tex="([^"]*)">[\s\S]*?</div><!--/eq-->')
PLAIN = re.compile(r'<div class="eq">[\s\S]*?</div>')


def render(texs):
    res = subprocess.run(['node', str(TOOLS / 'katex_render.js')], input=json.dumps([{'tex': t, 'display': True} for t in texs]),
                         capture_output=True, text=True, check=True)
    out = json.loads(res.stdout)
    bad = [(t, r['error']) for t, r in zip(texs, out) if 'error' in r]
    if bad:
        for t, e in bad:
            print('KaTeX error:', e, '\n   in:', t[:160])
        raise SystemExit(1)
    return [r['html'] for r in out]


def katex_css():
    css = (KATEX / 'katex.min.css').read_text()

    def embed(m):
        rule = m.group(0)
        fn = re.search(r'url\(fonts/(KaTeX_[\w-]+)\.woff2\)', rule).group(1)
        data = base64.b64encode((KATEX / 'fonts' / f'{fn}.woff2').read_bytes()).decode()
        return re.sub(r'src:[^;}]*', f'src:url(data:font/woff2;base64,{data}) format("woff2")', rule)
    keep = ('Main', 'Math', 'AMS', 'Size1', 'Size2', 'Size3', 'Size4')
    css = re.sub(r'@font-face\{[^}]*\}', lambda m: embed(m) if re.search(r'font-family:KaTeX_(%s);' % '|'.join(keep), m.group(0)) else '', css)
    return css


CSS = katex_css()
for name, texs in PAGES.items():
    path = ROOT / name
    s = path.read_text()
    if BLOCK.search(s):                                   # already converted: re-render from data-tex
        texs = [html.unescape(m.group(1)) for m in BLOCK.finditer(s)]
        pattern = BLOCK
    else:
        n = len(PLAIN.findall(s))
        if n != len(texs):
            raise SystemExit(f'{name}: {n} plain equation blocks, {len(texs)} transcriptions')
        pattern = PLAIN
    rendered = iter(render(texs))
    texs_iter = iter(texs)

    def put(_m):
        t = next(texs_iter)
        return (f'<div class="eq tex" data-tex="{html.escape(t, quote=True)}" role="img" aria-label="{html.escape(re.sub(chr(10), " ", t), quote=True)}">'
                f'{next(rendered)}</div><!--/eq-->')
    s = pattern.sub(put, s)
    block = '/*KATEX-BEGIN*/\n' + CSS + '\n/*KATEX-END*/'
    if '/*KATEX-BEGIN*/' in s:
        s = re.sub(r'/\*KATEX-BEGIN\*/[\s\S]*?/\*KATEX-END\*/', lambda m: block, s)
    else:
        i = s.index('</style>')
        s = s[:i] + block + '\n' + s[i:]
    path.write_text(s)
    print(f'{name}: {len(texs)} equation blocks typeset')
