// Extract the physics block from hydraulic_control.html, run the default cycle and both loop analyses,
// write control_runs.json.   Usage: node dump_control.js
const fs = require('fs');
const path = require('path');

const html = fs.readFileSync(path.join(__dirname, 'hydraulic_control.html'), 'utf8');
const block = html.match(/\/\*PHYSICS-BEGIN\*\/([\s\S]*?)\/\*PHYSICS-END\*\//);
if (!block) throw new Error('physics markers not found in hydraulic_control.html');
const api = new Function(`${block[1]}\nreturn { C0, DEFAULTS, MODES, makePlant, equilibrium, simulate, analyse, expm, eigenvalues };`)();

const P = { ...api.DEFAULTS };
const t0 = Date.now();
const run = api.simulate(P);
const keep = ['t', 'mode', 'yr', 'Fr', 'force', 'y', 'yd', 'xv', 'uCmd', 'uApp', 'pa', 'Qh', 'pA', 'pB', 'F', 'W', 'Lv', 'Lh', 'Lf', 'Ws', 'Wst', 'Ec', 'stored', 'closure'];
const rec = {};
for (const k of keep) rec[k] = run.rec[k];
const out = {
  C0: api.C0, P,
  run: { outcome: run.outcome, tEnd: run.tEnd, events: run.events, eq0: run.eq0, closureMax: run.closureMax, substeps: run.substeps, pMin: run.pMin, rec },
  analysis: {}
};
for (const loop of ['position', 'force']) {
  const a = api.analyse(P, loop);
  out.analysis[loop] = {
    eq: a.eq, x0: a.x0, u0: a.u0, scale: a.scale, A: a.A, B: a.B, C: a.C, As: a.As, Bs: a.Bs, Cs: a.Cs,
    Phi: a.Phi, Gam: a.Gam, Acl: a.Acl, olPoles: a.olPoles, clPoles: a.clPoles, maxAbsZ: a.maxAbsZ, stable: a.stable,
    margins: a.margins, ctrl: a.ctrl, freq: a.freq
  };
  const m = a.margins;
  console.log(`${loop.padEnd(9)} stable=${a.stable} max|z|=${a.maxAbsZ.toFixed(6)} PM=${m.pm.toFixed(2)} deg at ${m.fc.toFixed(2)} Hz  GM=${m.gm.toFixed(2)} dB at ${m.fg.toFixed(1)} Hz`);
}
fs.writeFileSync(path.join(__dirname, 'control_runs.json'), JSON.stringify(out));
const ev = run.events.map(e => `${e.mode}@${e.t.toFixed(3)}`).join(' ');
console.log(`cycle: outcome=${run.outcome} tEnd=${run.tEnd.toFixed(3)} s  closureMax=${run.closureMax.toExponential(2)} J  (${((Date.now() - t0) / 1000).toFixed(2)} s)`);
console.log(`events: ${ev}`);
console.log(`peak F = ${(Math.max(...run.rec.F) / 1000).toFixed(3)} kN, min p = ${(run.pMin / 1e6).toFixed(3)} MPa`);
console.log('wrote control_runs.json');
