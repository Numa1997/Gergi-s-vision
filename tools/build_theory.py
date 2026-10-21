#!/usr/bin/env python3
"""Build hydraulic_theory.html from theory/*.src.html.

The sources are HTML with LaTeX math: $...$ inline, $$...$$ display, \\tag{n} for an equation number and
\\boxed{...} around a whole display for a key result. Every formula is typeset here, at build time, with
KaTeX (tools/katex_render.js), and the KaTeX fonts are embedded, so the page looks the same in every
browser and runs no script library. Equation references like (4.5) in the text become links.

Usage: (cd tools && npm install) once, then python3 tools/build_theory.py
"""
import base64
import html
import json
import pathlib
import re
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOLS = ROOT / 'tools'
SRC = sorted((ROOT / 'theory').glob('*.src.html'))
TEMPLATE = (TOOLS / 'theory_template.html').read_text()
FONTS = (ROOT / 'fonts' / 'fonts-embedded.css').read_text().strip()
KATEX = TOOLS / 'node_modules' / 'katex' / 'dist'

body = '\n'.join(p.read_text() for p in SRC)
eq_ids = set()
jobs = []          # formulas to typeset: (tex, display)


def job(tex, display):
    """Queue a formula and return a placeholder that the typeset HTML replaces later."""
    jobs.append((tex, display))
    return f'\x00{len(jobs) - 1}\x00'


BREAKS = [
    (re.compile(r'\\q?quad\s*\\Rightarrow\s*\\q?quad'), True),
    (re.compile(r'\\;\s*\\Rightarrow\s*\\;'), True),
    (re.compile(r'\\Rightarrow(?![A-Za-z])'), True),
    (re.compile(r'\\qquad(?![A-Za-z])'), False),
    (re.compile(r'\\quad(?![A-Za-z])'), False),
]


def split_top(tex):
    pieces, start, i, depth = [], 0, 0, 0
    while i < len(tex):
        c = tex[i]
        if c == '\\' and re.match(r'\\(left|begin)(?![A-Za-z])', tex[i:]):
            depth += 1
        elif c == '\\' and re.match(r'\\(right|end)(?![A-Za-z])', tex[i:]):
            depth -= 1
        elif c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
        if depth == 0 and c == '\\':
            for pat, keep in BREAKS:
                m = pat.match(tex, i)
                if m:
                    pieces.append(tex[start:i])
                    start = i + m.group(0).index('\\Rightarrow') if keep else m.end()
                    i = m.end()
                    break
            else:
                i += 1
            continue
        i += 1
    pieces.append(tex[start:])
    return [p.strip() for p in pieces if p.strip()]


def display(m):
    tex = html.unescape(m.group(1).strip())
    tag = re.search(r'\\tag\{([^}]*)\}', tex)
    num = None
    if tag:
        num = tag.group(1)
        tex = (tex[:tag.start()] + tex[tag.end():]).strip()
    boxed = tex.startswith(r'\boxed{') and tex.endswith('}')
    if boxed:
        tex = re.sub(r'^(\\;|\s)+|(\\;|\s)+$', '', tex[len(r'\boxed{'):-1])
    pieces = [tex] if r'\begin{aligned}' in tex else split_top(tex)
    math = '<div class="eqs">' + ''.join(job(p, True) for p in pieces) + '</div>'
    attrs = ''
    if num:
        eq_ids.add(num)
        attrs = f' id="eq-{num}"'
    cls = 'eqn boxed' if boxed else 'eqn'
    no = f'<span class="eqno">({num})</span>' if num else '<span class="eqno"></span>'
    return f'<div class="{cls}"{attrs}>{math}{no}</div>'


def inline(m):
    ph = job(html.unescape(m.group(1).strip()), False)
    punct = m.group(2) or ''
    return f'<span class="nobr">{ph}{punct}</span>' if punct else ph


body = re.sub(r'\$\$(.+?)\$\$', display, body, flags=re.S)
body = re.sub(r'\$([^$\n]+?)\$([.,:;)]?)', inline, body)
if '$' in body:
    raise SystemExit('unmatched $ left in the source')

# Equation references become links. The math is still a placeholder here, so no link can land inside it.
body = re.sub(r'\((\d+\.\d+)\)', lambda m: f'<a href="#eq-{m.group(1)}">({m.group(1)})</a>' if m.group(1) in eq_ids else m.group(0), body)

# Typeset every formula in one batch.
res = subprocess.run(['node', str(TOOLS / 'katex_render.js')], input=json.dumps([{'tex': t, 'display': d} for t, d in jobs]),
                     capture_output=True, text=True, check=True)
rendered = json.loads(res.stdout)
errors = [(jobs[k][0], r['error']) for k, r in enumerate(rendered) if 'error' in r]
if errors:
    for tex, err in errors:
        print('KaTeX error:', err, '\n   in:', tex[:160])
    raise SystemExit(f'{len(errors)} formulas failed')


def place(m):
    k = int(m.group(1))
    tex, disp = jobs[k]
    label = html.escape(re.sub(r'\s+', ' ', tex), quote=True)
    return f'<span class="{"kd" if disp else "ki"}" role="img" aria-label="{label}">{rendered[k]["html"]}</span>'


body = re.sub(r'\x00(\d+)\x00', place, body)

# KaTeX's stylesheet with the fonts it actually uses embedded as data URIs.
css = (KATEX / 'katex.min.css').read_text()
used = set()


def embed(m):
    rule = m.group(0)
    fam = re.search(r'font-family:KaTeX_(\w+)', rule).group(1)
    fn = re.search(r'url\(fonts/(KaTeX_[\w-]+)\.woff2\)', rule).group(1)
    data = base64.b64encode((KATEX / 'fonts' / f'{fn}.woff2').read_bytes()).decode()
    used.add(fn)
    return re.sub(r'src:[^;}]*', f'src:url(data:font/woff2;base64,{data}) format("woff2")', rule)


# keep only the families that typeset this text: main, math, AMS, the size variants for big delimiters
keep = ('Main', 'Math', 'AMS', 'Size1', 'Size2', 'Size3', 'Size4', 'Caligraphic')
css = re.sub(r'@font-face\{[^}]*\}', lambda m: embed(m) if re.search(r'font-family:KaTeX_(%s);' % '|'.join(keep), m.group(0)) else '', css)
FONTS += '\n/* KaTeX ' + json.loads((KATEX.parent / 'package.json').read_text())['version'] + ', MIT licence; fonts: ' + ', '.join(sorted(used)) + ' */\n' + css

# Contents from the chapters and part banners.
toc, toc_m = [], []
for m in re.finditer(r'<div class="part"><span class="part-n">([^<]+)</span><span class="part-t">([^<]+)</span></div>|<section id="([^"]+)" class="chapter">\s*<h2><span class="chn">([^<]+)</span>\s*([^<]+)</h2>', body):
    if m.group(1):
        toc.append(f'<li class="part-li">{m.group(1)}</li>')
    else:
        sid, n, title = m.group(3), m.group(4), m.group(5).strip()
        toc.append(f'<li><a href="#{sid}"><span class="n">{n}</span><span>{title}</span></a></li>')
        toc_m.append(f'<li><a href="#{sid}">{n} · {title}</a></li>')

n_ch = len(re.findall(r'class="chapter"', body))
n_eq = len(eq_ids)
n_fig = len(re.findall(r'<figure class="fig">', body))
stats = (f'<span class="chip"><b>{n_ch}</b> chapters</span><span class="chip"><b>{n_eq}</b> numbered equations</span>'
         f'<span class="chip"><b>{n_fig}</b> figures</span><span class="chip">every number computed from the model</span>')

out = (TEMPLATE.replace('{{FONTS}}', FONTS).replace('{{TOC}}', '\n'.join(toc)).replace('{{TOC_MOBILE}}', '\n'.join(toc_m))
       .replace('{{STATS}}', stats).replace('{{BODY}}', body))
(ROOT / 'hydraulic_theory.html').write_text(out)
print(f'wrote hydraulic_theory.html: {len(out)} bytes, {n_ch} chapters, {n_eq} equations, {n_fig} figures, {len(jobs)} formulas')
