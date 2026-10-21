#!/usr/bin/env python3
"""Independent check of the hydraulic-press physics in hydraulic.html.

Steps
  1. Run dump_runs.js: Node extracts the code between /*PHYSICS-BEGIN*/ and /*PHYSICS-END*/
     and writes runs.json for four cases.
  2. sympy: build T and V from the parts of the machine, derive the Euler-Lagrange equation,
     and compare it with the formula the JavaScript integrates.
  3. sympy: show that the pressure field closes on both piston equations.
  4. scipy solve_ivp (DOP853, rtol 1e-10): re-integrate every case with its own state machine
     and compare end time, x(t), p1(t), p2(t) with the JavaScript run.
  5. Energy closure W = K + V + E_lost for both integrations.

Usage: python3 check_physics.py      (exit code 0 when every check passes)
"""
import json
import pathlib
import subprocess
import sys

import numpy as np
import sympy as sp
from scipy.integrate import solve_ivp

HERE = pathlib.Path(__file__).resolve().parent

# Constants typed in from the specification, not read from the JavaScript.
G, RHO, H0, STROKE, M1, M2 = 9.81, 870.0, 0.40, 0.30, 2.0, 10.0
HOLD, STALL_WAIT, TIME_LIMIT = 0.6, 1.0, 10.0

TOL = {'t_end': 1e-6, 'x': 1e-7, 'p': 1.0, 'closure': 1e-6, 'selftest': 1e-6, 'a_rel': 1e-9}
failures = []


def check(name, value, limit):
    ok = value < limit
    if not ok:
        failures.append(name)
    print(f"    {name:<44} {value:12.3e}   (limit {limit:.0e})  {'PASS' if ok else 'FAIL'}")


# ------------------------------------------------------------------ 1. JavaScript runs
print("1. JavaScript runs (node dump_runs.js)")
subprocess.run(['node', str(HERE / 'dump_runs.js')], check=True)
runs = json.loads((HERE / 'runs.json').read_text())['cases']

# ------------------------------------------------------------------ 2. Lagrangian with sympy
print("\n2. Equation of motion from the Lagrangian (sympy)")
t = sp.symbols('t')
F, A1, A2, Ap, Lp, m1, mL, rho, g, H = sp.symbols('F A1 A2 A_p L_p m1 mL rho g H0', positive=True)
X = sp.Function('x')(t)
Xd = X.diff(t)
r, q = A1 / A2, A1 / Ap
h1, h2 = H - X, H + r * X
half = sp.Rational(1, 2)
# kinetic energy, part by part: input piston, output piston + load, left column, pipe plug, right column
T = half * (m1 * Xd**2 + mL * (r * Xd)**2 + rho * A1 * h1 * Xd**2
            + rho * Ap * Lp * (q * Xd)**2 + rho * A2 * h2 * (r * Xd)**2)
# potential: piston faces at h1 and h2, oil columns with centres of mass at h/2 (pipe oil does not move vertically)
Vabs = m1 * g * h1 + mL * g * h2 + rho * g * (A1 * h1**2 + A2 * h2**2) / 2
V = Vabs - Vabs.subs(X, 0)
Lag = T - V
EL = sp.diff(Lag.diff(Xd), t) - Lag.diff(X) - F          # Euler-Lagrange with generalized force F
a_lagrange = sp.solve(sp.Eq(EL, 0), X.diff(t, 2))[0]

x, v, a = sp.symbols('x v a')
to_xv = lambda e: e.subs(Xd, v).subs(X, x)
a_lagrange = to_xv(a_lagrange)

# the formula the JavaScript integrates (as written in hydraulic.html)
mu_js = m1 + mL * r**2 + rho * A1 * ((H - x) + r * (H + r * x) + Lp * A1 / Ap)
dmu_js = rho * A1 * (r**2 - 1)
V_js = -m1 * g * x + mL * g * r * x + half * rho * g * A1 * (1 + r) * x**2
dV_js = -m1 * g + mL * g * r + rho * g * A1 * (1 + r) * x
a_js = (F - dV_js - half * dmu_js * v**2) / mu_js

checks = {
    'mu(x) = 2T / xdot^2': sp.simplify(to_xv(2 * T) / v**2 - mu_js),
    'dmu/dx': sp.simplify(sp.diff(mu_js, x) - dmu_js),
    'V(x) from the parts': sp.simplify(to_xv(V) - V_js),
    'dV/dx': sp.simplify(sp.diff(V_js, x) - dV_js),
    'xddot(Euler-Lagrange) - xddot(JS)': sp.simplify(a_lagrange - a_js),
}
for name, residual in checks.items():
    ok = residual == 0
    if not ok:
        failures.append(name)
    print(f"    {name:<44} residual = {residual}   {'PASS' if ok else 'FAIL'}")

# ------------------------------------------------------------------ 3. pressure field
print("\n3. Pressure field against both piston equations (sympy)")
p1 = (F + m1 * g - m1 * a) / A1                      # input piston:  m1 a = F + m1 g - p1 A1
p2 = mL * (g + r * a) / A2                           # output piston: mL r a = p2 A2 - mL g
vp = q * v
pb1 = p1 + rho * (g - a) * (H - x)
pin = pb1 + half * rho * (v**2 - vp**2)
pout = pin - rho * q * a * Lp
pb2 = pout + half * rho * (vp**2 - r**2 * v**2)
ptop = pb2 - rho * (g + r * a) * (H + r * x)
a_field = sp.solve(sp.Eq(ptop, p2), a)[0]
dp_expected = rho * a * ((H - x) + r * (H + r * x) + Lp * q) + half * rho * (r**2 - 1) * v**2 + rho * g * (1 + r) * x
pchecks = {
    'p_top - p2 with a from Lagrange': sp.simplify((ptop - p2).subs(a, a_js)),
    'a solved from field + pistons - a(JS)': sp.simplify(a_field - a_js),
    'p1 - p_top - [inertia + Bernoulli + head]': sp.simplify(p1 - ptop - dp_expected),
}
for name, residual in pchecks.items():
    ok = residual == 0
    if not ok:
        failures.append(name)
    print(f"    {name:<44} residual = {residual}   {'PASS' if ok else 'FAIL'}")
print("    p1 - p2 = rho*a*(h1 + r*h2 + Lp*A1/Ap) + (rho/2)(r^2 - 1)v^2 + rho*g*(1 + r)*x")


# ------------------------------------------------------------------ 4. independent integration
class Model:
    def __init__(self, P):
        self.P = P
        self.A1 = np.pi * P['d1']**2 / 4
        self.A2 = np.pi * P['d2']**2 / 4
        self.Ap = np.pi * P['dp']**2 / 4
        self.r, self.q = self.A1 / self.A2, self.A1 / self.Ap
        self.mL = M2 + P['M']
        self.F1min = self.mL * G * self.r - M1 * G
        self.k = RHO * G * self.A1 * (1 + self.r)

    def force(self, t):
        return self.P['F1'] * min(max(t, 0.0) / self.P['tau'], 1.0) if self.P['tau'] > 0 else self.P['F1']

    def mu(self, x):
        r = self.r
        return M1 + self.mL * r**2 + RHO * self.A1 * ((H0 - x) + r * (H0 + r * x) + self.P['Lp'] * self.q)

    def V(self, x):
        return -M1 * G * x + self.mL * G * self.r * x + 0.5 * self.k * x**2

    def acc(self, t, x, v):
        dmu = RHO * self.A1 * (self.r**2 - 1)
        dV = -M1 * G + self.mL * G * self.r + self.k * x
        return (self.force(t) - dV - 0.5 * dmu * v**2) / self.mu(x)

    def p1p2(self, phase, t, x, a):
        h1, h2 = H0 - x, H0 + self.r * x
        if phase == 1:
            return (self.force(t) + M1 * G - M1 * a) / self.A1, self.mL * (G + self.r * a) / self.A2
        if phase == 0:
            p1 = (self.force(t) + M1 * G) / self.A1
            return p1, p1 + RHO * G * (h1 - h2)
        p2 = self.mL * G / self.A2
        return p2 + RHO * G * (h2 - h1), p2


def integrate(P):
    m = Model(P)
    stalls = not (P['F1'] > m.F1min)
    t_stop = P['tau'] + (STALL_WAIT if stalls else TIME_LIMIT)
    outcome = 'stalled' if stalls else 'time limit'
    tt, x0, v0, W, lost, phase = 0.0, 0.0, 0.0, 0.0, 0.0, 0
    pieces, events = [], []

    def rhs(t_, y):
        return [y[1], m.acc(t_, y[0], y[1]), m.force(t_) * y[1]]

    def ev_stroke(t_, y):
        return y[0] - STROKE
    ev_stroke.terminal, ev_stroke.direction = True, 1

    def ev_floor(t_, y):
        return y[0]
    ev_floor.terminal, ev_floor.direction = True, -1

    while tt < t_stop:
        if phase == 0:
            if stalls:
                td = np.inf
            elif m.F1min < 0 or P['tau'] == 0:
                td = tt
            else:
                td = max(tt, P['tau'] * m.F1min / P['F1'])   # exact: the ramp is linear
            t1 = min(td, t_stop)
            pieces.append(dict(t0=tt, t1=t1, phase=0, sol=None, x=x0, W=W, lost=lost))
            tt = t1
            if td < t_stop:
                phase = 1
                events.append(('departure', td))
        elif phase == 1:
            t1 = P['tau'] if tt < P['tau'] < t_stop else t_stop       # restart at the ramp's kink
            sol = solve_ivp(rhs, (tt, t1), [x0, v0, W], method='DOP853', rtol=1e-10, atol=1e-13,
                            dense_output=True, events=[ev_stroke, ev_floor])
            if sol.status == 1:
                hit = 0 if sol.t_events[0].size else 1
                te, ye = sol.t_events[hit][0], sol.y_events[hit][0]
                xe = STROKE if hit == 0 else 0.0
                dK = 0.5 * m.mu(xe) * ye[1]**2
                pieces.append(dict(t0=tt, t1=te, phase=1, sol=sol, lost=lost))
                lost += dK
                tt, x0, v0, W = te, xe, 0.0, ye[2]
                if hit == 0:
                    phase, t_stop, outcome = 2, te + HOLD, 'stroke stop'
                    events.append(('stroke stop', te, ye[1], dK))
                else:
                    phase = 0
                    events.append(('fell back', te, ye[1], dK))
            else:
                pieces.append(dict(t0=tt, t1=t1, phase=1, sol=sol, lost=lost))
                tt = t1
                x0, v0, W = sol.y[:, -1]
        else:
            pieces.append(dict(t0=tt, t1=t_stop, phase=2, sol=None, x=x0, W=W, lost=lost))
            tt = t_stop
    return m, pieces, events, outcome, tt


def state_at(pieces, tq):
    pc = pieces[-1]
    for p in pieces:
        if p['t0'] <= tq <= p['t1']:
            pc = p
            if tq < p['t1']:
                break
    if pc['sol'] is None:
        return pc['phase'], pc['x'], 0.0, pc['W'], pc['lost']
    xq, vq, Wq = pc['sol'].sol(min(max(tq, pc['t0']), pc['t1']))
    return 1, xq, vq, Wq, pc['lost']


print("\n4. Re-integration with scipy solve_ivp (DOP853, rtol 1e-10) and 5. energy closure")
a_num = sp.lambdify((x, v, F, A1, A2, Ap, Lp, m1, mL, rho, g, H), a_lagrange, 'numpy')
for name, run in runs.items():
    P = run['P']
    m, pieces, events, outcome, t_end = integrate(P)
    R = {k: np.asarray(val, dtype=float) for k, val in run['rec'].items()}
    print(f"\n  case {name}: F1 = {P['F1']:.4f} N, M = {P['M']} kg, d1 = {P['d1']} m, d2 = {P['d2']} m, "
          f"tau = {P['tau']} s, Lp = {P['Lp']} m, dp = {P['dp']} m")
    print(f"    outcome JS = {run['outcome']!r}, Python = {outcome!r};  t_end JS = {run['tEnd']:.9f} s, "
          f"Python = {t_end:.9f} s;  F1,min = {m.F1min:.6f} N")
    if run['outcome'] != outcome:
        failures.append(f'{name}: outcome')
        print("    outcome mismatch  FAIL")
    check('|t_end(JS) - t_end(Python)| [s]', abs(run['tEnd'] - t_end), TOL['t_end'])
    if name.startswith('turnback'):
        check('F1 - (F1,min + 1 N) [N]', abs(P['F1'] - m.F1min - 1.0), 1e-9)

    ph_py = np.empty(R['t'].size, int)
    x_py, v_py, W_py, L_py = (np.empty(R['t'].size) for _ in range(4))
    for i, tq in enumerate(R['t']):
        ph_py[i], x_py[i], v_py[i], W_py[i], L_py[i] = state_at(pieces, tq)
    a_py = np.array([m.acc(tq, xx, vv) if ph == 1 else 0.0 for tq, xx, vv, ph in zip(R['t'], x_py, v_py, ph_py)])
    pp = np.array([m.p1p2(ph, tq, xx, aa) for ph, tq, xx, aa in zip(ph_py, R['t'], x_py, a_py)])
    K_py = 0.5 * np.array([m.mu(xx) for xx in x_py]) * v_py**2
    V_py = np.array([m.V(xx) for xx in x_py])

    mismatched = int(np.sum(ph_py != R['phase']))
    print(f"    frames compared: {R['t'].size}, phase mismatches: {mismatched}")
    if mismatched:
        failures.append(f'{name}: phase')
    check('max |x(JS) - x(Python)| [m]', np.max(np.abs(R['x'] - x_py)), TOL['x'])
    check('max |p1(JS) - p1(Python)| [Pa]', np.max(np.abs(R['p1'] - pp[:, 0])), TOL['p'])
    check('max |p2(JS) - p2(Python)| [Pa]', np.max(np.abs(R['p2'] - pp[:, 1])), TOL['p'])
    mov = R['phase'] == 1
    if mov.any():
        a_ref = a_num(R['x'][mov], R['v'][mov], R['F'][mov], m.A1, m.A2, m.Ap, P['Lp'], M1, m.mL, RHO, G, H0)
        check('max |a(JS) - a(sympy)| / max|a| [-]', np.max(np.abs(R['a'][mov] - a_ref)) / np.max(np.abs(a_ref)), TOL['a_rel'])
    check('JS energy closure max|W-K-V-lost| [J]', np.max(np.abs(R['W'] - R['K'] - R['V'] - R['L'])), TOL['closure'])
    check('Python energy closure max|W-K-V-lost| [J]', np.max(np.abs(W_py - K_py - V_py - L_py)), TOL['closure'])
    check('JS pressure-chain self-test |p_top-p2| [Pa]', run['selfTest'], TOL['selftest'])

    # facts about the run, for the report
    print(f"    x_max = {100 * R['x'].max():.3f} cm, x2_max = {1000 * m.r * R['x'].max():.3f} mm, "
          f"v_min = {R['v'].min():.4f} m/s, W_end = {R['W'][-1]:.4f} J, lost = {R['L'][-1]:.4f} J")
    print(f"    lowest gauge pressure = {run['pmin'] / 1000:.2f} kPa ({run['pminWhere']}, t = {run['pminT']:.3f} s), "
          f"highest = {run['pmax'] / 1000:.2f} kPa")
    for e in events:
        if e[0] == 'departure':
            print(f"    Python event: departure at t = {e[1]:.9f} s")
        else:
            print(f"    Python event: {e[0]} at t = {e[1]:.9f} s, impact speed {e[2]:.6f} m/s, {e[3]:.6f} J lost")

print()
if failures:
    print(f"FAILED: {len(failures)} check(s): {', '.join(failures)}")
    sys.exit(1)
print("ALL CHECKS PASSED")
