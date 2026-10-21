#!/usr/bin/env python3
"""Independent check of the servo-hydraulic press in hydraulic_control.html.

Steps
  1. node dump_control.js: runs the page's physics block (default cycle + both loop analyses) -> control_runs.json
  2. Equilibria: scipy fsolve on an independent Python model vs the JS Newton solver.
  3. Linearization: sympy Jacobian of the Python model at both operating points vs the JS finite differences.
  4. Zero-order hold: scipy.linalg.expm vs the JS scaling-and-squaring Taylor series.
  5. Eigenvalues: numpy vs the JS balance + Hessenberg + shifted-QR routine; closed loop rebuilt in Python.
  6. Loop gain L(e^{jwT}) and margins recomputed in Python.
  7. Nonlinear sampled-data cycle re-simulated with scipy solve_ivp (DOP853) between samples, same supervisor.
  8. Energy audit closure.

Usage: python3 check_control.py      (exit code 0 when every check passes)
"""
import json
import math
import pathlib
import subprocess
import sys

import numpy as np
import sympy as sp
from scipy.integrate import solve_ivp
from scipy.linalg import expm
from scipy.optimize import fsolve

HERE = pathlib.Path(__file__).resolve().parent
failures = []


def check(name, value, limit):
    ok = bool(value < limit)
    if not ok:
        failures.append(name)
    print(f"    {name:<58} {value:11.3e}  (limit {limit:.0e})  {'PASS' if ok else 'FAIL'}")


print("1. JavaScript cycle and loop analyses (node dump_control.js)")
subprocess.run(['node', str(HERE / 'dump_control.js')], check=True)
data = json.loads((HERE / 'control_runs.json').read_text())
P = data['P']
JS = data['analysis']

# ------------------------------------------------------------------ independent Python model
# Constants retyped from the theory section of the page.
rho, nu, patm, npoly, g, pT = 870.0, 32e-6, 101325.0, 1.4, 9.81, 0.0
QN, dpN, ptr, zetaV, KL = 100 / 60000, 7e6, 1e5, 0.7, 2e-13
Va0, D, dr, S, VA0, VB0 = 1.5e-4, 0.12, 0.08, 0.20, 3e-4, 2e-4
mRam, bv, vs, vstr, kst = 10.0, 2000.0, 1e-3, 5e-3, 1.3
yc, zetaW, kStop, zetaStop, fTurb, Kminor = 0.12, 0.05, 2e8, 0.7, 0.02, 1.5
Tf, vCreep, Fswitch, Frelease = 0.002, 0.01, 1000.0, 1000.0
tSettle, Tapp, appGap, Tramp, Thold, Tret, tTail, tMax = 0.1, 1.0, 0.002, 0.25, 0.5, 1.8, 0.3, 10.0
yOp, vOp = 0.06, 0.1

m = mRam + P['M']
AA = math.pi * D**2 / 4
AB = AA - math.pi * dr**2 / 4
Ah = math.pi * P['dh']**2 / 4
Vh = Ah * P['Lh']
Iner = rho * P['Lh'] / Ah
Rlam = 128 * rho * nu * P['Lh'] / (math.pi * P['dh']**4)
Kt = rho * (fTurb * P['Lh'] / P['dh'] + Kminor) / (2 * Ah**2)
Kv = QN / math.sqrt(dpN / 2)
wv = 2 * math.pi * P['fv']
cw = 2 * zetaW * math.sqrt(P['kw'] * m)
cs = 2 * zetaStop * math.sqrt(kStop * m)
Va = Va0 + Vh / 2
ps = P['ps']


def beta(p):
    pabs = max(p + patm, 1.0)
    ar = P['alpha0'] / (1 - P['alpha0']) * (patm / pabs) ** (1 / npoly)
    return P['betaOil'] * (1 + ar) / (1 + ar * P['betaOil'] / (npoly * pabs))


def gq(dp):
    return dp / (dp * dp + ptr * ptr) ** 0.25


def flows(xv, pa, pB):
    xh = min(1.0, max(-1.0, xv))
    xp, xn = max(xh, 0.0), min(xh, 0.0)
    QA = Kv * (xp * gq(ps - pa) + xn * gq(pa - pT)) + KL * (ps - 2 * pa + pT)
    QB = -Kv * (xp * gq(pB - pT) + xn * gq(ps - pB)) + KL * (ps - 2 * pB + pT)
    QS = Kv * (xp * gq(ps - pa) - xn * gq(ps - pB)) + KL * (2 * ps - pa - pB)
    return QA, QB, QS


def dpf(Q):
    return Rlam * Q + Kt * Q * abs(Q)


def fric(v):
    return P['Fc'] * math.tanh(v / vs) * (1 + (kst - 1) * math.exp(-(v / vstr) ** 2)) + bv * v


def contact(y, v):
    return max(0.0, P['kw'] * (y - yc) + cw * v) if y > yc else 0.0


def stop(y, v):
    return max(0.0, -kStop * y - cs * v) if y < 0 else 0.0


def rhs(t, x, u):
    xv, vv, pa, Qh, pA, pB, y, yd = x[:8]
    QA, QB, QS = flows(xv, pa, pB)
    VA = VA0 + Vh / 2 + AA * y
    VB = VB0 + AB * (S - y)
    dph, Ff, Fw, Fs = dpf(Qh), fric(yd), contact(y, yd), stop(y, yd)
    return [
        vv, wv * wv * (u - xv) - 2 * zetaV * wv * vv,
        beta(pa) / Va * (QA - Qh), (pa - pA - dph) / Iner,
        beta(pA) / VA * (Qh - AA * yd), beta(pB) / VB * (QB + AB * yd),
        yd, (pA * AA - pB * AB - m * g - Ff - Fw + Fs) / m,
        ps * QS, ps * QS - pa * QA - pB * QB, dph * Qh, Ff * yd, Fw * yd, -Fs * yd,
        pa * (QA - Qh) + pA * (Qh - AA * yd) + pB * (QB + AB * yd),
    ]


def equilibrium(y0, v0, guess):
    Qh = AA * v0
    load = m * g + fric(v0) + contact(y0, v0) - stop(y0, v0)

    def res(z):
        xv, pA, pB = z[0], z[1] * ps, z[2] * ps
        QA, QB, _ = flows(xv, pA + dpf(Qh), pB)
        return [(QA - Qh) / QN, (QB + AB * v0) / QN, (pA * AA - pB * AB - load) / (ps * AA)]
    z = fsolve(res, [guess['xv'], guess['pA'] / ps, guess['pB'] / ps], xtol=1e-14, full_output=True)[0]
    return {'xv': z[0], 'pA': z[1] * ps, 'pB': z[2] * ps, 'pa': z[1] * ps + dpf(Qh), 'Qh': Qh}


# ------------------------------------------------------------------ 2. equilibria
print("\n2. Operating points (scipy fsolve vs JS Newton)")
eq_py = {}
for loop, (y0, v0) in {'hover': (0.0, 0.0), 'position': (yOp, vOp), 'force': (yc + P['Fref'] / P['kw'], 0.0)}.items():
    eq_js = data['run']['eq0'] if loop == 'hover' else JS[loop]['eq']
    guess = {'xv': eq_js['xv'] * (1 + 0.05) + 1e-4, 'pA': eq_js['pA'] * 0.97, 'pB': eq_js['pB'] * 1.03}
    e = equilibrium(y0, v0, guess)
    eq_py[loop] = e
    err = max(abs(e['xv'] - eq_js['xv']), abs(e['pA'] - eq_js['pA']) / ps, abs(e['pB'] - eq_js['pB']) / ps)
    print(f"    {loop:<9} y0 = {1000 * y0:7.2f} mm  v0 = {v0:4.2f} m/s   xv = {100 * e['xv']:9.5f} %  "
          f"pA = {e['pA'] / 1e6:8.5f} MPa  pB = {e['pB'] / 1e6:8.5f} MPa")
    check(f'{loop}: max |Δ| (xv, pA/ps, pB/ps)', err, 1e-9)

# ------------------------------------------------------------------ 3. sympy Jacobian
print("\n3. Linearization: sympy Jacobian vs JS central differences (scaled coordinates)")
xs = sp.symbols('xv vv pa Qh pA pB y yd', real=True)
us = sp.Symbol('u', real=True)


def symbolic_rhs(xv_sign, in_contact):
    xv, vv, pa, Qh, pA, pB, y, yd = xs
    G = lambda d: d / (d**2 + ptr**2) ** sp.Rational(1, 4)
    xp = xv if xv_sign > 0 else 0
    xn = xv if xv_sign < 0 else 0
    QA = Kv * (xp * G(ps - pa) + xn * G(pa - pT)) + KL * (ps - 2 * pa + pT)
    QB = -Kv * (xp * G(pB - pT) + xn * G(ps - pB)) + KL * (ps - 2 * pB + pT)
    B = lambda p: P['betaOil'] * (1 + P['alpha0'] / (1 - P['alpha0']) * (patm / (p + patm)) ** (1 / sp.Float(npoly))) / \
        (1 + P['alpha0'] / (1 - P['alpha0']) * (patm / (p + patm)) ** (1 / sp.Float(npoly)) * P['betaOil'] / (npoly * (p + patm)))
    VA = VA0 + Vh / 2 + AA * y
    VB = VB0 + AB * (S - y)
    Ff = P['Fc'] * sp.tanh(yd / vs) * (1 + (kst - 1) * sp.exp(-(yd / vstr) ** 2)) + bv * yd
    Fw = P['kw'] * (y - yc) + cw * yd if in_contact else 0
    dph = Rlam * Qh + Kt * Qh * sp.Abs(Qh)
    return sp.Matrix([
        vv, wv**2 * (us - xv) - 2 * zetaV * wv * vv,
        B(pa) / Va * (QA - Qh), (pa - pA - dph) / Iner,
        B(pA) / VA * (Qh - AA * yd), B(pB) / VB * (QB + AB * yd),
        yd, (pA * AA - pB * AB - m * g - Ff - Fw) / m])


lin_py = {}
for loop in ['position', 'force']:
    a = JS[loop]
    x0 = a['x0']
    f = symbolic_rhs(np.sign(x0[0]), loop == 'force')
    J = sp.lambdify((xs, us), f.jacobian(xs), 'numpy')
    Bj = sp.lambdify((xs, us), f.diff(us), 'numpy')
    A_py = np.array(J(x0, a['u0']), dtype=float)
    B_py = np.array(Bj(x0, a['u0']), dtype=float).ravel()
    T = np.diag(a['scale'])
    Ti = np.linalg.inv(T)
    As_py, Bs_py = Ti @ A_py @ T, Ti @ B_py
    As_js, Bs_js = np.array(a['As']), np.array(a['Bs'])
    lin_py[loop] = (As_py, Bs_py, np.array(a['Cs']))
    rel = np.max(np.abs(As_py - As_js)) / np.max(np.abs(As_py))
    check(f'{loop}: max |A_sympy - A_JS| / max |A|', rel, 1e-6)
    check(f'{loop}: max |B_sympy - B_JS| / max |B|', np.max(np.abs(Bs_py - Bs_js)) / np.max(np.abs(Bs_py)), 1e-6)

# ------------------------------------------------------------------ 4-6. ZOH, eigenvalues, loop gain
print("\n4-6. Zero-order hold, eigenvalues, loop gain and margins")


def controller(loop, Ts):
    if loop == 'position':
        a, bd = Tf / (Tf + Ts), P['Kd'] / (Tf + Ts)
        return (np.array([[1, 0, 0], [0, a, -bd], [0, 0, 0]], float), np.array([P['Ki'] * Ts, bd, 1.0]),
                np.array([1, a, -bd], float), P['Kp'] + P['Ki'] * Ts + bd)
    return np.array([[1.0]]), np.array([P['KiF'] * Ts]), np.array([1.0]), P['KpF'] + P['KiF'] * Ts


def closed_loop(Phi, Gam, Cs, ctrl):
    Ac, Bc, Cc, Dc = ctrl
    n, ns = Phi.shape[0], Ac.shape[0]
    M = np.zeros((n + ns + 1, n + ns + 1))
    M[:n, :n], M[:n, -1] = Phi, Gam
    M[n:n + ns, :n], M[n:n + ns, n:n + ns] = -np.outer(Bc, Cs), Ac
    M[-1, :n], M[-1, n:n + ns] = -Dc * Cs, Cc
    return M


def match(ev_a, ev_b):
    """Largest distance from an eigenvalue in a to its nearest in b, relative to max(|lambda|, 1)."""
    b = np.array(ev_b)
    return max(np.min(np.abs(b - z)) / max(abs(z), 1.0) for z in ev_a)


Ts = P['Ts']
for loop in ['position', 'force']:
    a = JS[loop]
    As_js, Bs_js, Cs = np.array(a['As']), np.array(a['Bs']), np.array(a['Cs'])
    n = As_js.shape[0]
    Maug = np.zeros((n + 1, n + 1))
    Maug[:n, :n], Maug[:n, n] = As_js * Ts, Bs_js * Ts
    E = expm(Maug)
    check(f'{loop}: max |Phi_scipy - Phi_JS| (expm, same A)', np.max(np.abs(E[:n, :n] - np.array(a['Phi']))), 1e-10)
    check(f'{loop}: max |Gam_scipy - Gam_JS| (expm, same A)', np.max(np.abs(E[:n, n] - np.array(a['Gam']))), 1e-10)
    ol_js = [complex(*z) for z in a['olPoles']]
    cl_js = [complex(*z) for z in a['clPoles']]
    check(f'{loop}: open-loop eigenvalues numpy vs JS QR', match(np.linalg.eigvals(As_js), ol_js), 1e-9)
    check(f'{loop}: closed-loop eigenvalues numpy vs JS QR', match(np.linalg.eigvals(np.array(a['Acl'])), cl_js), 1e-9)
    # physics chain rebuilt entirely in Python: sympy A -> scipy expm -> closed loop -> numpy eig
    As_py, Bs_py, _ = lin_py[loop]
    Maug[:n, :n], Maug[:n, n] = As_py * Ts, Bs_py * Ts
    E = expm(Maug)
    ctrl = controller(loop, Ts)
    cl_py = np.linalg.eigvals(closed_loop(E[:n, :n], E[:n, n], Cs, ctrl))
    check(f'{loop}: closed-loop poles, Python chain vs JS', match(cl_py, cl_js), 1e-5)
    print(f"    {loop}: max |z| Python = {np.max(np.abs(cl_py)):.6f}, JS = {a['maxAbsZ']:.6f}, stable = {a['stable']}")
    # loop gain on the JS frequency grid
    Phi, Gam = np.array(a['Phi']), np.array(a['Gam'])
    f = np.array(a['freq']['f'])
    z = np.exp(1j * 2 * np.pi * f * Ts)
    Gz = np.array([Cs @ np.linalg.solve(zz * np.eye(n) - Phi, Gam) for zz in z])
    if loop == 'position':
        Kz = P['Kp'] + P['Ki'] * Ts * z / (z - 1) + P['Kd'] * (z - 1) / ((Tf + Ts) * z - Tf)
    else:
        Kz = P['KpF'] + P['KiF'] * Ts * z / (z - 1)
    L = Kz * Gz / z
    L_js = np.array(a['freq']['Lre']) + 1j * np.array(a['freq']['Lim'])
    check(f'{loop}: max |L_py - L_JS| / |L_py|', np.max(np.abs(L - L_js) / np.abs(L)), 1e-8)
    ph = np.degrees(np.unwrap(np.angle(L)))
    ph -= 360 * math.ceil(ph[0] / 360) if ph[0] > 0 else 0
    while ph[0] <= -360:
        ph += 360
    mag = np.abs(L)
    k = np.where(np.diff(np.sign(mag - 1)) != 0)[0][0]
    s = math.log(mag[k]) / (math.log(mag[k]) - math.log(mag[k + 1]))
    phi = ph[k] + s * (ph[k + 1] - ph[k])
    pm = 180 + phi - 360 * math.ceil(phi / 360)
    print(f"    {loop}: phase margin Python {pm:.3f}°, JS {a['margins']['pm']:.3f}°;  gain margin JS {a['margins']['gm']:.3f} dB "
          f"at {a['margins']['fg']:.2f} Hz")
    check(f'{loop}: |PM_py - PM_JS| [deg]', abs(pm - a['margins']['pm']), 0.05)

# ------------------------------------------------------------------ 7. nonlinear cycle
print("\n7. Nonlinear cycle: scipy solve_ivp (DOP853, rtol 1e-9) between samples, same supervisor")
MODES = ['settle', 'approach', 'creep', 'press', 'release', 'retract', 'done']


def quintic(tau):
    s_ = min(1.0, max(0.0, tau))
    return s_**3 * (10 - 15 * s_ + 6 * s_ * s_), 30 * s_ * s_ * (1 - s_) ** 2


def simulate():
    eq0 = eq_py['hover']
    x = np.zeros(15)
    x[0], x[2], x[4], x[5] = eq0['xv'], eq0['pa'], eq0['pA'], eq0['pB']
    a, bd = Tf / (Tf + Ts), P['Kd'] / (Tf + Ts)
    Kff = AA / (Kv * math.sqrt(ps / 2))
    yT = yc - appGap
    st = dict(mode='settle', t0=0.0, I=eq0['xv'], D=0.0, ePrev=0.0, IF=0.0, yStart=0.0, FStart=0.0, uPend=eq0['xv'])
    events, rows = [], []
    scale = np.array([1, wv, ps, QN, ps, ps, 0.01, 0.1] + [1e3] * 7)
    k = 0
    while True:
        t = k * Ts
        yM, FM = x[6], contact(x[6], x[7])
        uApp = st['uPend']
        tm = t - st['t0']

        def enter(md):
            st['mode'], st['t0'] = md, t
            events.append((md, t))
        if st['mode'] == 'settle' and tm >= tSettle - 1e-12:
            enter('approach'); st['yStart'] = 0.0
        elif st['mode'] == 'approach' and tm >= Tapp - 1e-12:
            enter('creep'); st['yStart'] = yT
        elif st['mode'] == 'creep' and FM > Fswitch:
            enter('press'); st['FStart'] = FM; st['IF'] = st['uPend']
        elif st['mode'] == 'press' and tm >= Tramp + Thold - 1e-12:
            enter('release')
        elif st['mode'] == 'release' and tm >= Tramp - 1e-12:
            enter('retract'); st.update(yStart=yM, I=st['uPend'], D=0.0, ePrev=0.0)
        elif st['mode'] == 'retract' and tm >= Tret - 1e-12:
            enter('done')
        tau = t - st['t0']
        yr = vr = Fr = 0.0
        force = False
        md = st['mode']
        if md == 'approach':
            q, dq = quintic(tau / Tapp); yr = st['yStart'] + (yT - st['yStart']) * q; vr = (yT - st['yStart']) * dq / Tapp
        elif md == 'creep':
            yr, vr = st['yStart'] + vCreep * tau, vCreep
        elif md == 'press':
            force, Fr = True, st['FStart'] + (P['Fref'] - st['FStart']) * min(tau / Tramp, 1)
        elif md == 'release':
            force, Fr = True, P['Fref'] + (Frelease - P['Fref']) * min(tau / Tramp, 1)
        elif md == 'retract':
            q, dq = quintic(tau / Tret); yr, vr = st['yStart'] * (1 - q), -st['yStart'] * dq / Tret
        accept = lambda v, e: abs(v) <= 1 or (v > 1 and e < 0) or (v < -1 and e > 0)
        if force:
            e = Fr - FM; Ic = st['IF'] + P['KiF'] * Ts * e; v = P['KpF'] * e + Ic
            if accept(v, e):
                st['IF'] = Ic
            else:
                v = P['KpF'] * e + st['IF']
        else:
            e = yr - yM
            st['D'] = a * st['D'] + bd * (e - st['ePrev']); st['ePrev'] = e
            Ic = st['I'] + P['Ki'] * Ts * e
            v = P['Kp'] * e + Ic + st['D'] + Kff * vr
            if accept(v, e):
                st['I'] = Ic
            else:
                v = P['Kp'] * e + st['I'] + st['D'] + Kff * vr
        u = min(1.0, max(-1.0, v))
        st['uPend'] = u
        rows.append((t, MODES.index(md), x[6], FM, x[4], x[5], x[0], u, x[2], x[3], x[7], *x[8:15]))
        if md == 'done' and t >= st['t0'] + tTail - 1e-12:
            break
        if t >= tMax:
            break
        sol = solve_ivp(lambda tt, xx: rhs(tt, xx, uApp), (t, t + Ts), x, method='DOP853',
                        rtol=1e-9, atol=1e-9 * scale)
        x = sol.y[:, -1]
        k += 1
    return events, np.array(rows)


events_py, R = simulate()
js = data['run']
rec = {key: np.array(v, float) for key, v in js['rec'].items()}
print(f"    Python events: {' '.join(f'{md}@{t:.3f}' for md, t in events_py)}")
print(f"    JS events:     {' '.join(f'{e['mode']}@{e['t']:.3f}' for e in js['events'])}")
same_events = len(events_py) == len(js['events']) and all(
    md == e['mode'] and abs(t - e['t']) < 1e-12 for (md, t), e in zip(events_py, js['events']))
print(f"    mode switches at identical samples: {same_events}")
if not same_events:
    failures.append('event sequence')
nmin = min(len(R), len(rec['t']))
check('|t_end(Python) - t_end(JS)| [s]', abs(R[-1, 0] - js['tEnd']), 1e-9)
check('max |y_py - y_JS| [m]', np.max(np.abs(R[:nmin, 2] - rec['y'][:nmin])), 1e-6)
check('max |F_py - F_JS| [N]', np.max(np.abs(R[:nmin, 3] - rec['F'][:nmin])), 20.0)
check('max |p_A,py - p_A,JS| [Pa]', np.max(np.abs(R[:nmin, 4] - rec['pA'][:nmin])), 2e3)
check('max |p_B,py - p_B,JS| [Pa]', np.max(np.abs(R[:nmin, 5] - rec['pB'][:nmin])), 2e3)
check('max |u_py - u_JS| [-]', np.max(np.abs(R[:nmin, 7] - rec['uCmd'][:nmin])), 1e-3)
print(f"    peak force: Python {R[:, 3].max() / 1000:.4f} kN, JS {rec['F'].max() / 1000:.4f} kN")

# ------------------------------------------------------------------ 8. energy audit
print("\n8. Energy audit: W_pump = kinetic + height + hose slug + compression + losses + specimen + stop")
y_init = 0.0
stored = 0.5 * m * R[:, 10] ** 2 + m * g * (R[:, 2] - y_init) + 0.5 * Iner * R[:, 9] ** 2 + R[:, 17]
closure_py = R[:, 11] - stored - R[:, 12] - R[:, 13] - R[:, 14] - R[:, 15] - R[:, 16]
W_end = R[-1, 11]
print(f"    pump work {W_end / 1000:.4f} kJ, valve loss {R[-1, 12] / 1000:.4f} kJ, hose {R[-1, 13] / 1000:.4f} kJ, "
      f"seals {R[-1, 14] / 1000:.4f} kJ, specimen {R[-1, 15] / 1000:.4f} kJ")
check('Python closure max |residual| / W_pump', np.max(np.abs(closure_py)) / W_end, 1e-6)
check('JS closure max |residual| / W_pump', js['closureMax'] / W_end, 1e-6)

print()
if failures:
    print(f"FAILED: {len(failures)} check(s): {', '.join(failures)}")
    sys.exit(1)
print("ALL CHECKS PASSED")
