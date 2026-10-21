#!/usr/bin/env python3
"""One-off assembly of the redesigned hydraulic.html (kept for the record). The physics block is copied unchanged."""
import pathlib, re, sys
SP = pathlib.Path(sys.argv[1])
root = pathlib.Path(__file__).resolve().parents[1]
old = (SP / 'hydraulic.prev.html').read_text()
ctl = (root / 'hydraulic_control.html').read_text()
physics = old[old.index('/*PHYSICS-BEGIN*/'): old.index('/*PHYSICS-END*/') + len('/*PHYSICS-END*/')]
# the shared design system: take the control page's second <style> block
styles = re.findall(r'<style>([\s\S]*?)</style>', ctl)
css = styles[1]
css = css.replace("/* Layout: an instrument bench. The plant drawing with its gauge cluster leads; live tiles and knobs sit beside it.\n   Below: the key to the drawing, the time traces, the loop analysis, the theory, and the worked solutions.\n   One column on a phone. */",
                  "/* Layout: a lab bench. The true-scale press and its dial strip lead; live tiles and knobs sit beside it;\n   time traces and the physics follow. One column on a phone. */")
css += """
.crosslinks { display: flex; flex-wrap: wrap; gap: 10px; }
.crosslinks a { font: 500 14px var(--f-text); color: var(--wine); text-decoration: none; border: 1.5px solid var(--wine); border-radius: 999px; padding: 6px 14px; background: var(--paper); }
.crosslinks a:hover { background: var(--wine); color: #fbf3e8; }
.physics p, .physics li { max-width: 78ch; }
.physics ul { padding-left: 22px; }
"""
fonts = (root / 'fonts' / 'fonts-embedded.css').read_text().strip()
body = (SP / 'ideal_body.html').read_text()
phys = (SP / 'ideal_physics_section.html').read_text()
phys = phys.replace('<section class="box physics" aria-label="Physics">\n    <h2>Physics</h2>',
                    '<section class="box physics theory" aria-label="Physics">\n    <div class="eyebrow">Theory in brief</div><h2>Physics</h2>\n    <p class="note" style="margin-bottom: 8px">The short version. Every step is derived in full in <a href="hydraulic_theory.html">Hydraulics from First Principles</a>, Part I.</p>')
ui = (SP / 'ideal_ui.js').read_text()
head = f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Ideal Hydraulic Press</title>
<meta name="claude:viewport-fit-sides" content="cover">
<style>
/*FONTS-BEGIN*/
{fonts}
/*FONTS-END*/
</style>
<style>{css}</style>
</head>
<body>
'''
out = head + body + phys + '\n</div>\n\n<script>\n' + physics + '\n' + ui + '</script>\n</body>\n</html>\n'
(root / 'hydraulic.html').write_text(out)
print('wrote', len(out), 'bytes')
