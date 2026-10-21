#!/usr/bin/env python3
"""One-off assembly of the redesigned hydraulic_control.html from its parts (kept for the record)."""
import pathlib, re, sys
SP = pathlib.Path(sys.argv[1])
root = pathlib.Path(__file__).resolve().parents[1]
old = (SP / 'hydraulic_control.prev.html').read_text()

physics = old[old.index('/*PHYSICS-BEGIN*/'): old.index('/*PHYSICS-END*/') + len('/*PHYSICS-END*/')]
a = "enter('press', t); S.FStart = FM; S.IF = S.uPend; }"
assert physics.count(a) == 1
physics = physics.replace(a, "enter('press', t); S.FStart = FM; S.IF = P.noBumpless ? 0 : S.uPend; }   // noBumpless: problem 8")

sec = old[old.index('  <section class="box" aria-label="Key to the drawing and the symbols">'): old.index('<script>')]
sec = sec[:sec.rindex('</div>')]          # drop the closing tag of .wrap

def rep(s, o, n):
    assert s.count(o) == 1, o
    return s.replace(o, n)
sec = rep(sec, '<h2>Key to the drawing</h2>', '<div class="eyebrow">Legend</div><h2>Key to the drawing</h2>')
sec = rep(sec, '    <h2>Symbols</h2>', '    <div class="eyebrow" style="margin-top: 6px">Notation</div><h2>Symbols</h2>')
sec = rep(sec, '<section class="box" aria-label="Time traces">\n    <h2>Time traces</h2>',
          '<section class="box" aria-label="Time traces">\n    <div class="eyebrow">Recorded every sample</div><h2 style="margin-bottom: 12px">Time traces</h2>')
sec = rep(sec, '<section class="box" aria-label="Loop analysis">\n    <h2>Loop analysis</h2>',
          '<section class="box" aria-label="Loop analysis" id="analysis">\n    <div class="eyebrow">Small-signal stability</div><h2 style="margin-bottom: 12px">Loop analysis</h2>')
sec = rep(sec, '<h2>The model, equation by equation</h2>', '<div class="eyebrow">Theory</div><h2>The model, equation by equation</h2>')
extra = '''      <li><svg viewBox="0 0 48 32" aria-hidden="true"><circle cx="24" cy="16" r="14" fill="#efe4d1" stroke="#4b423c" stroke-width="2"/><path d="M24 16 L33 9" stroke="#23160f" stroke-width="2"/><path d="M13 22 A12 12 0 0 1 20 5" stroke="#7d1d2f" stroke-width="3" fill="none"/></svg><span><b>Gauge panel dials.</b> Pressures p_a, p_A, p_B, the specimen force F and the spool x_v. The wine arc fills up to the reading; on the spool dial the thin blue needle is the command u, so you can see the spool lag behind it.</span></li>
      <li><svg viewBox="0 0 48 32" aria-hidden="true"><rect x="2" y="9" width="44" height="14" rx="7" fill="#7d1d2f"/><circle cx="10" cy="16" r="3" fill="#fbf3e8"/></svg><span><b>Mode stepper.</b> The row above the drawing: green dots are finished modes, the wine pill is the active one. Select a mode to jump to its start.</span></li>
'''
sec = rep(sec, '    </ul>\n    <div class="eyebrow" style="margin-top: 6px">Notation</div>', extra + '    </ul>\n    <div class="eyebrow" style="margin-top: 6px">Notation</div>')
sec = sec.replace('<b>Torque motor.</b> Turns the electrical command u into spool motion; it lags with bandwidth f<sub>v</sub>.',
                  '<b>Torque motor.</b> Turns the electrical command u into spool motion; its armature (wine bar) tilts with u, and the spool follows with bandwidth f<sub>v</sub>.')
# problem list: link each problem to its worked solution
ol = sec[sec.index('<ol class="problems">'): sec.index('</ol>', sec.index('<ol class="problems">'))]
items = ol.split('</li>')
new_items = [it + (f' <a href="#sol-{n + 1}">Worked solution ↓</a>' if n < len(items) - 1 else '') for n, it in enumerate(items)]
sec = sec.replace(ol, '</li>'.join(new_items))

def block(start, end):
    return old[old.index(start): old.index(end)]
key = block('// ---------------------------------------------------------------- key to the symbols', '// ---------------------------------------------------------------- time plots')
plots = block('// ---------------------------------------------------------------- time plots', '// ---------------------------------------------------------------- analysis plots')
anal = block('// ---------------------------------------------------------------- analysis plots', '// ---------------------------------------------------------------- readouts and loop')

part1 = (SP / 'ctl_part1.html').read_text()
sols = (SP / 'ctl_solutions.html').read_text()
ui_a = (SP / 'ctl_ui_a.js').read_text()
ui_b = (SP / 'ctl_ui_b.js').read_text()
fonts = (root / 'fonts' / 'fonts-embedded.css').read_text()
part1 = part1.replace('/*FONTS-BEGIN*/\n/*FONTS-END*/', '/*FONTS-BEGIN*/\n' + fonts.strip() + '\n/*FONTS-END*/')

out = part1 + sec + '\n' + sols + '</div>\n\n<script>\n' + physics + '\n\n' + ui_a + key + plots + anal + ui_b + '</script>\n</body>\n</html>\n'
(root / 'hydraulic_control.html').write_text(out)
print('wrote', len(out), 'bytes')
