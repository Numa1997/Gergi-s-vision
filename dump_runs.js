// Extract the physics block from hydraulic.html, run the four test cases, write runs.json.
// Usage: node dump_runs.js
const fs = require('fs');
const path = require('path');

const html = fs.readFileSync(path.join(__dirname, 'hydraulic.html'), 'utf8');
const block = html.match(/\/\*PHYSICS-BEGIN\*\/([\s\S]*?)\/\*PHYSICS-END\*\//);
if (!block) throw new Error('physics markers not found in hydraulic.html');
const api = new Function(`${block[1]}\nreturn { CONST, DEFAULTS, makeModel, simulate };`)();

const base = api.DEFAULTS;
const F1min = api.makeModel(base).F1min;
const cases = {
  defaults: { ...base },
  stall_F1_100N: { ...base, F1: 100 },
  turnback_F1min_plus_1N: { ...base, F1: F1min + 1 },
  pipe_dp_0p5cm: { ...base, dp: 0.005 }
};

const keep = ['t', 'x', 'v', 'a', 'phase', 'F', 'p1', 'p2', 'ptop', 'W', 'K', 'V', 'L'];
const out = { CONST: api.CONST, cases: {} };
for (const [name, P] of Object.entries(cases)) {
  const run = api.simulate(P);
  const m = run.model;
  const rec = {};
  for (const key of keep) rec[key] = run.rec[key];
  out.cases[name] = {
    P, F1min: m.F1min, r: m.r, A1: m.A1, A2: m.A2, Ap: m.Ap,
    outcome: run.outcome, tEnd: run.tEnd, events: run.events,
    selfTest: run.selfTest, closure: run.closure,
    pmin: run.pmin, pminWhere: run.pminWhere, pminT: run.pminT, pmax: run.pmax,
    rec
  };
  console.log(`${name.padEnd(24)} outcome=${run.outcome.padEnd(12)} tEnd=${run.tEnd.toFixed(6)} s  frames=${run.rec.t.length}`);
}
fs.writeFileSync(path.join(__dirname, 'runs.json'), JSON.stringify(out));
console.log('wrote runs.json');
