#!/usr/bin/env python3
"""Build hydraulic_theory.html from theory/*.src.html.

The sources are HTML with LaTeX math: $...$ inline, $$...$$ display, \\tag{n} for an equation number and
\\boxed{...} around a whole display for a key result. Math is converted to MathML here, at build time, so the
page needs no script library at run time. Equation references like (4.5) in the text become links.

Usage: python3 tools/build_theory.py        (needs: pip install latex2mathml)
"""
import html
import pathlib
import re

from latex2mathml.converter import convert

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = sorted((ROOT / 'theory').glob('*.src.html'))
TEMPLATE = (ROOT / 'tools' / 'theory_template.html').read_text()
FONTS = (ROOT / 'fonts' / 'fonts-embedded.css').read_text().strip()
MATH_FONT = ROOT / 'fonts' / 'math-embedded.css'          # Noto Sans Math subset with its MATH table (tools/build_math_font.py)
if MATH_FONT.exists():
    FONTS += '\n' + MATH_FONT.read_text().strip()

body = '\n'.join(p.read_text() for p in SRC)
eq_ids = set()


def inner(tex):
    """MathML for a fragment, without the outer <math> element."""
    # display mode, as the cells of aligned are: big operators take their limits underneath
    mml = convert(tex, display='block') if tex.strip() else '<math><mrow></mrow></math>'
    return re.sub(r'^<math[^>]*>|</math>$', '', mml)


def aligned(tex):
    """latex2mathml cannot lay out aligned: build an <mtable> with right/left alternating columns ourselves."""
    body_ = re.search(r'\\begin\{aligned\}(.*)\\end\{aligned\}', tex, re.S).group(1)
    rows = [r for r in re.split(r'\\\\', body_) if r.strip()]
    trs = []
    for r in rows:
        cells = r.split('&')
        # cells of aligned are in display style, as in LaTeX: full-size fractions and limits
        tds = ''.join(f'<mtd class="{"ar" if j % 2 == 0 else "al"}"><mstyle displaystyle="true" scriptlevel="0">{inner(c)}</mstyle></mtd>'
                      for j, c in enumerate(cells))
        trs.append(f'<mtr>{tds}</mtr>')
    return f'<math xmlns="http://www.w3.org/1998/Math/MathML" display="block"><mtable class="aligned">{"".join(trs)}</mtable></math>'


# Top-level break points of a display equation: "⇒" (kept, it starts the next piece) and
# \quad / \qquad (dropped; the flex gap replaces them). Pieces sit on one line when the
# column is wide and wrap onto new lines on a phone. "Top level" means outside braces,
# \left...\right pairs and \begin...\end environments.
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
    if r'\begin{aligned}' in tex:
        mml = '<div class="eqs">' + aligned(tex) + '</div>'
    else:
        mml = '<div class="eqs">' + ''.join(convert(seg, display='block') for seg in split_top(tex)) + '</div>'
    attrs = ''
    if num:
        eq_ids.add(num)
        attrs = f' id="eq-{num}"'
    cls = 'eqn boxed' if boxed else 'eqn'
    no = f'<span class="eqno">({num})</span>' if num else '<span class="eqno"></span>'
    return f'<div class="{cls}"{attrs}>{mml}{no}</div>'


def inline(m):
    mml = convert(html.unescape(m.group(1).strip()))
    punct = m.group(2) or ''
    return f'<span class="nobr">{mml}{punct}</span>' if punct else mml


body = re.sub(r'\$\$(.+?)\$\$', display, body, flags=re.S)
body = re.sub(r'\$([^$\n]+?)\$([.,:;)]?)', inline, body)
if '$' in body:
    raise SystemExit('unmatched $ left in the source')

# Time-derivative dots: latex2mathml writes \dot and \ddot as plain over-scripts, which
# MathML sets small and high, drifting toward the exponent. As accents they sit on the letter.
body = re.sub(r'<mover>(<mrow>(?:(?!</?mover).)*?</mrow>)<mo>(&#x002D9;|&#x000A8;)</mo></mover>',
              r'<mover accent="true">\1<mo>\2</mo></mover>', body)

# Link equation references, outside <math> only.
parts = re.split(r'(<math[\s\S]*?</math>)', body)
for i in range(0, len(parts), 2):
    parts[i] = re.sub(r'\((\d+\.\d+)\)', lambda m: f'<a href="#eq-{m.group(1)}">({m.group(1)})</a>' if m.group(1) in eq_ids else m.group(0), parts[i])
body = ''.join(parts)

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
print(f'wrote hydraulic_theory.html: {len(out)} bytes, {n_ch} chapters, {n_eq} equations, {n_fig} figures')
