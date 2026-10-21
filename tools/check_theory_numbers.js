// Check that every "In our press" number the theory quotes is what the simulation models compute.
//
// The models are the physics blocks of the two interactive pages; the quotes come from the theory page.
// Given hydraulics.html (the combined page), all three are taken from the copies embedded in it, so the
// check covers exactly what a reader of that page sees. Given nothing, the standalone pages are used.
//
// Usage: node tools/check_theory_numbers.js [hydraulics.html]
const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..');
const arg = process.argv[2];
let pages;
if (arg) {
  const combined = fs.readFileSync(path.resolve(arg), 'utf8');
  const page = id => {
    const m = combined.match(new RegExp(`<script type="application/json" id="page-${id}">([\\s\\S]*?)</script>`));
    if (!m) throw new Error(`page-${id} not found in ${arg}`);
    return JSON.parse(m[1]);
  };
  pages = { servo: page('servo'), ideal: page('ideal'), theory: page('theory') };
} else {
  const read = f => fs.readFileSync(path.join(ROOT, f), 'utf8');
  pages = { servo: read('hydraulic_control.html'), ideal: read('hydraulic.html'), theory: read('hydraulic_theory.html') };
}

function physics(html, names) {
  const block = html.match(/\/\*PHYSICS-BEGIN\*\/([\s\S]*?)\/\*PHYSICS-END\*\//);
  if (!block) throw new Error('physics markers not found');
  return new Function(`${block[1]}\nreturn { ${names.join(', ')} };`)();
}

// The theory as plain text: no styles, no MathML copies of the formulas, no tags, one space between words.
const text = pages.theory
  .replace(/<style[\s\S]*?<\/style>/g, '')
  .replace(/<span class="katex-mathml">[\s\S]*?<\/math><\/span>/g, '')
  .replace(/<[^>]+>/g, ' ')
  .replace(/&nbsp;/g, ' ').replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&#x27;|&#39;/g, "'")
  .replace(/[​  ]/g, ' ')
  .replace(/−/g, '-')
  .replace(/\s+/g, ' ');

let failed = 0, n = 0;
// `quote` must appear in the theory within `span` characters after `anchor`; `quote` is built from the model.
function expect(label, anchor, quote, span = 400) {
  n++;
  const i = text.indexOf(anchor);
  const ok = i >= 0 && text.slice(i, i + span).includes(quote);
  if (!ok) failed++;
  console.log(`${ok ? 'ok  ' : 'FAIL'}  ${label}: model gives "${quote}"${ok ? '' : `, not found after "${anchor}"`}`);
}
const f1 = x => x.toFixed(1), f2 = x => x.toFixed(2);

// ---------------------------------------------------------------- the servo press
const S = physics(pages.servo, ['C0', 'DEFAULTS', 'simulate', 'analyse']);
const P = { ...S.DEFAULTS };
const run = S.simulate(P);
const last = k => run.rec[k][run.rec[k].length - 1];
const W = last('W'), Lv = last('Lv');
const pos = S.analyse(P, 'position'), frc = S.analyse(P, 'force');

n++;
if (run.outcome === 'complete') console.log(`ok    the default press cycle completes (${run.tEnd.toFixed(3)} s)`);
else { failed++; console.log(`FAIL  the default press cycle ended as "${run.outcome}"`); }

expect('position loop margins', 'Position loop:',
  `Position loop: ${f1(pos.margins.pm)}° and ${f1(pos.margins.gm)} dB, crossover ${f1(pos.margins.fc)} Hz`);
expect('force loop margins', 'Position loop:',
  `Force loop: ${f1(frc.margins.pm)}° and ${f1(frc.margins.gm)} dB, crossover ${f1(frc.margins.fc)} Hz`);
expect('pump work, valve heat', 'Over one cycle',
  `the pump does ${f1(W / 1e3)} kJ of work and the valve burns ${f1(Lv / 1e3)} kJ of it: ${Math.round(100 * Lv / W)} %`);

const ce = pos.eq, he = frc.eq;
expect('cruise: spool opening', 'Cruising up at 0.1 m/s at y = 60 mm', `${f1(100 * ce.xv)} %`);
expect('cruise: cap pressure', 'Cruising up at 0.1 m/s at y = 60 mm', `${f2(ce.pA / 1e6)} MPa`);
expect('cruise: rod pressure', 'Cruising up at 0.1 m/s at y = 60 mm', `${f2(ce.pB / 1e6)} MPa`);
expect('cruise: valve drop', 'Cruising up at 0.1 m/s, the spool', `${f2((P.ps - ce.pa) / 1e6)} MPa`);
expect('hold 60 kN: spool opening', 'Holding 60 kN: x', `${(100 * he.xv).toFixed(3)} %`);
expect('hold 60 kN: cap pressure', 'Holding 60 kN: x', `${f2(he.pA / 1e6)} MPa`);
expect('hold 60 kN: rod pressure', 'Holding 60 kN: x', `${f2(he.pB / 1e6)} MPa`);
expect('hold 60 kN: force balance', 'Holding 60 kN needs',
  `p A = ${f1(he.pA / 1e6)} MPa under the piston against p B = ${f1(he.pB / 1e6)} MPa`);

const slow = S.analyse({ ...P, Ts: 0.004 }, 'position');
expect('phase margin lost at Ts = 4 ms', 'The measured phase margin', `falls by ${f1(pos.margins.pm - slow.margins.pm)}°`);
const hot = S.analyse({ ...P, Kp: 900 }, 'position');
n++;
if (pos.stable && !hot.stable) console.log('ok    90 %/mm position gain: closed-loop poles leave the unit circle (default gain is stable)');
else { failed++; console.log(`FAIL  stability: default ${pos.stable}, at 90 %/mm ${hot.stable}`); }

const Kv = S.C0.QN / Math.sqrt(S.C0.dpN / 2);
expect('valve flow coefficient', 'Q N = 100 L/min at 7 MPa', `${f2(Kv * 1e7)} × 1 0 - 7`);
const I = S.C0.rho * P.Lh / (Math.PI * P.dh ** 2 / 4);
expect('hose inertance', '2 m of 12 mm hose: I',`I = ${f2(I / 1e7)} × 1 0 7`);
expect('force ramp and hold times', 'It ramps the force to 60 kN',
  `It ramps the force to ${P.Fref / 1e3} kN in ${S.C0.Tramp} s and holds it for ${S.C0.Thold} s`);

// ---------------------------------------------------------------- the ideal press
const I_ = physics(pages.ideal, ['CONST', 'DEFAULTS', 'makeModel', 'simulate']);
const m = I_.makeModel(I_.DEFAULTS);
expect('area ratio', 'd 1 = 4 cm and d 2 = 12 cm', `A 2 / A 1 = ${Math.round(m.A2 / m.A1)}`);
expect('force multiplied', 'd 1 = 4 cm and d 2 = 12 cm', `A push of ${I_.DEFAULTS.F1} N becomes ${Math.round(I_.DEFAULTS.F1 * m.A2 / m.A1)} N`);
expect('smallest push that lifts', 'F 1 , m i n', `= ${f2(m.F1min)} N`, 200);
expect('lift for the full stroke', 'the full 30 cm stroke', `lifts the load by ${(100 * I_.CONST.stroke * m.r).toFixed(2)} cm`);
expect('pipe speed ratio', 'The 1 cm pipe has', `A 1 / A p = ${Math.round(m.A1 / m.Ap)}`);
expect('effective mass at the start', 'The pipe holds only', `μ = ${f1(m.mu(0))} kg`);
const thin = I_.simulate({ ...I_.DEFAULTS, dp: 0.005 });
const tm = thin.model, vmax = Math.max(...thin.rec.v.map(Math.abs)) * tm.A1 / tm.Ap;
expect('5 mm pipe: oil speed', 'With a 5 mm pipe', `reaches ${f1(vmax)} m/s`);
expect('5 mm pipe: Bernoulli drop', 'With a 5 mm pipe', `≈ ${Math.round(0.5 * I_.CONST.rho * vmax ** 2 / 1e4) * 10} kPa`);
expect('5 mm pipe: lowest gauge pressure', 'With a 5 mm pipe', `falls to ${Math.round(thin.pmin / 1e3)} kPa`);

console.log(failed ? `\n${failed} OF ${n} CHECKS FAILED` : `\nALL ${n} THEORY NUMBERS MATCH THE MODELS`);
process.exit(failed ? 1 : 0);
