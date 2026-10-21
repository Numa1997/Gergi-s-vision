"""LaTeX for the equation blocks of the two interactive pages, in page order.

tools/render_page_math.py typesets these with KaTeX into the pages. Each block replaces one
plain-text <div class="eq"> the first time; after that the TeX lives in the block's data-tex
attribute and re-rendering is idempotent.
"""

CONTROL = [
# 0: valve and spool
r"""\begin{aligned}
&\ddot{x}_v + 2\zeta_v\omega_v\dot{x}_v + \omega_v^2x_v = \omega_v^2u,\qquad \omega_v = 2\pi f_v,\quad \zeta_v = 0.7\\
&\hat{x} = \operatorname{clamp}(x_v, -1, 1),\quad x^+ = \max(\hat{x}, 0),\quad x^- = \min(\hat{x}, 0)\\
&g(\Delta p) = \frac{\Delta p}{\left(\Delta p^2 + p_{\mathrm{tr}}^2\right)^{1/4}} \approx \operatorname{sign}(\Delta p)\sqrt{|\Delta p|}\\
&Q_A = K_v\left[x^+g(p_s - p_a) + x^-g(p_a - p_T)\right] + K_L(p_s - 2p_a + p_T)\\
&Q_B = -K_v\left[x^+g(p_B - p_T) + x^-g(p_s - p_B)\right] + K_L(p_s - 2p_B + p_T)\\
&Q_S = K_v\left[x^+g(p_s - p_a) - x^-g(p_s - p_B)\right] + K_L(2p_s - p_a - p_B)\\
&K_v = \frac{Q_N}{\sqrt{\Delta p_N/2}},\quad Q_N = 100\ \mathrm{L/min}\ \text{at}\ \Delta p_N = 7\ \mathrm{MPa},\quad K_L = 2\times10^{-13}\ \mathrm{m^3/(s\,Pa)}
\end{aligned}""",
# 1: air in the oil
r"""\begin{aligned}
&\alpha(p) = \frac{\alpha_0}{1 - \alpha_0}\left(\frac{p_0}{p_{\mathrm{abs}}}\right)^{1/n},\qquad p_{\mathrm{abs}} = p + p_0\\
&\beta_{\mathrm{eff}}(p) = \beta_{\mathrm{oil}}\,\frac{1 + \alpha}{1 + \alpha\,\beta_{\mathrm{oil}}/(n\,p_{\mathrm{abs}})}
\end{aligned}""",
# 2: hose, chambers, ram, friction, contact
r"""\begin{aligned}
\dot{p}_a &= \frac{\beta(p_a)}{V_a}\,(Q_A - Q_h), \qquad V_a = V_{a0} + V_h/2\\
I\dot{Q}_h &= p_a - p_A - R_{\mathrm{lam}}Q_h - K_tQ_h|Q_h|, \qquad I = \frac{\rho L_h}{A_h},\quad R_{\mathrm{lam}} = \frac{128\,\eta L_h}{\pi d_h^4},\quad K_t = \frac{\rho\,(fL_h/d_h + K_m)}{2A_h^2}\\
\dot{p}_A &= \frac{\beta(p_A)}{V_{A0} + V_h/2 + A_Ay}\,(Q_h - A_A\dot{y})\\
\dot{p}_B &= \frac{\beta(p_B)}{V_{B0} + A_B(S - y)}\,(Q_B + A_B\dot{y})\\
m\ddot{y} &= p_AA_A - p_BA_B - mg - F_f(\dot{y}) - F_w(y, \dot{y}) + F_{\mathrm{stop}}(y, \dot{y})\\
F_f &= F_c\tanh\!\left(\frac{\dot{y}}{v_s}\right)\left[1 + (k_{\mathrm{st}} - 1)\,e^{-(\dot{y}/v_{\mathrm{str}})^2}\right] + b_v\dot{y} \qquad \text{Stribeck: break-away } 1.3\,F_c\\
F_w &= \max\left(0,\ k_w\delta + c_w\dot{\delta}\right),\quad \delta = y - y_c > 0 \qquad \text{the specimen pushes, never pulls}\\
F_{\mathrm{stop}} &= \max\left(0,\ -k_sy - c_s\dot{y}\right),\quad y < 0 \qquad \text{bottom stop}
\end{aligned}""",
# 3: the control laws
r"""\begin{aligned}
&\textbf{position:}\quad e_k = y_{\mathrm{ref}} - y_k\\
&\qquad D_k = \frac{T_f}{T_f + T_s}\,D_{k-1} + \frac{K_d}{T_f + T_s}\,(e_k - e_{k-1}) \qquad \text{filtered derivative, } T_f = 2\ \mathrm{ms}\\
&\qquad I_k = I_{k-1} + K_iT_s\,e_k \qquad \text{frozen while saturated in the same direction (anti-windup)}\\
&\qquad u_k = \operatorname{sat}\!\left(K_pe_k + I_k + D_k + K_{\mathrm{ff}}v_{\mathrm{ref}}\right),\qquad K_{\mathrm{ff}} = \frac{A_A}{K_v\sqrt{p_s/2}}\\
&\textbf{force:}\quad u_k = \operatorname{sat}\!\left(K_{pF}(F_{\mathrm{ref}} - F_k) + I_{F,k}\right),\qquad I_{F,k} = I_{F,k-1} + K_{iF}T_s\,(F_{\mathrm{ref}} - F_k)\\
&\textbf{switching:}\quad \text{the integrator of the new law is loaded with the last command, so } u \text{ does not jump}
\end{aligned}""",
# 4: discretization and the loop
r"""\begin{aligned}
&\exp\!\left(\begin{bmatrix}A & B\\ 0 & 0\end{bmatrix}T_s\right) = \begin{bmatrix}\Phi & \Gamma\\ 0 & 1\end{bmatrix},\qquad \Phi = e^{AT_s},\quad \Gamma = \int_0^{T_s} e^{A\sigma}\,d\sigma\,B\\
&G(z) = C\,(zI - \Phi)^{-1}\Gamma,\qquad K_{\mathrm{pos}}(z) = K_p + \frac{K_iT_s\,z}{z - 1} + \frac{K_d\,(z - 1)}{(T_f + T_s)\,z - T_f}\\
&L(z) = K(z)\,z^{-1}G(z),\qquad z = e^{j\omega T_s}\\
&\text{closed loop:}\quad \mathbf{x}^+ = \Phi\mathbf{x} + \Gamma w,\quad \mathbf{s}^+ = A_c\mathbf{s} - B_cC\mathbf{x},\quad w^+ = C_c\mathbf{s} - D_cC\mathbf{x}
\end{aligned}""",
# 5: solution 1, the oil spring
r"""\begin{aligned}
\delta p_A &= -\frac{\beta_AA_A}{V_A}\,\delta y, \qquad \delta p_B = +\frac{\beta_BA_B}{V_B}\,\delta y\\
\delta F &= A_A\,\delta p_A - A_B\,\delta p_B = -\left(\frac{\beta_AA_A^2}{V_A} + \frac{\beta_BA_B^2}{V_B}\right)\delta y = -k_h\,\delta y\\
\omega_h^2 &= k_h/m
\end{aligned}""",
# 6: solution 2, hose slosh
r"""\begin{aligned}
&I\dot{Q} = p_a - p_A,\qquad C_a\dot{p}_a = -Q,\qquad C_A\dot{p}_A = +Q\\
&\Rightarrow\quad I\ddot{Q} = -\left(\frac{1}{C_a} + \frac{1}{C_A}\right)Q \qquad\Rightarrow\qquad \omega^2 = \frac{1/C_a + 1/C_A}{I}
\end{aligned}""",
# 7: solution 3, the two flow gains
r"""\begin{aligned}
x_v > 0:&\quad Q_A = K_vx_v\sqrt{p_s - p_a} \quad\Rightarrow\quad K_q^+ = K_v\sqrt{p_s - p_a}\\
x_v < 0:&\quad Q_A = K_vx_v\sqrt{p_a - p_T} \quad\Rightarrow\quad K_q^- = K_v\sqrt{p_a}\qquad (p_T = 0)\\
&\quad \frac{K_q^+}{K_q^-} = \sqrt{\frac{p_s - p_a}{p_a}}
\end{aligned}""",
# 8: solution 4, friction slope
r"""\begin{aligned}
&\left.\frac{dF_f}{d\dot{y}}\right|_0 = \frac{F_ck_{\mathrm{st}}}{v_s} + b_v = \frac{800\times1.3}{0.001} + 2000 = 1.04\times10^6\ \mathrm{N\,s/m}\\
&\zeta = \frac{c}{2\sqrt{k_hm}},\quad k_h = 1.82\times10^8\ \mathrm{N/m}\ \text{at}\ y = 123\ \mathrm{mm},\quad m = 160\ \mathrm{kg}\quad\Rightarrow\quad \zeta = 3.05
\end{aligned}""",
# 9: solution 6, sampling lag
r"""\begin{aligned}
&\text{lag of the one-sample delay and the hold at the crossover:}\quad \varphi = \omega T_s + \tfrac12\,\omega T_s = 1.5\,\omega T_s\\
&f_c = 9.70\ \mathrm{Hz}:\quad T_s = 1\ \mathrm{ms} \to 3.49^\circ + 1.75^\circ = 5.2^\circ,\qquad T_s = 4\ \mathrm{ms} \to 13.97^\circ + 6.99^\circ = 21.0^\circ
\end{aligned}""",
# 10: solution 7, force-loop gain
r"""\begin{aligned}
&Q = \frac{V_A}{\beta}\,\dot{p}_A + A_A\dot{y},\qquad F \approx p_AA_A \approx k_w\delta \qquad\Rightarrow\qquad \dot{F} = \frac{k_{\mathrm{eff}}}{A_A}\,Q\\
&\frac{1}{k_{\mathrm{eff}}} = \frac{1}{k_w} + \frac{V_A}{\beta A_A^2},\qquad Q = K_qx_v \qquad\Rightarrow\qquad \dot{F} = K_Ix_v,\quad K_I = \frac{k_{\mathrm{eff}}K_q}{A_A}\\
&L \approx \frac{K_{pF}K_I}{j\omega} \quad\Rightarrow\quad \omega_c = K_{pF}K_I \quad\Rightarrow\quad K_{pF} = \frac{2\pi\cdot 10\ \mathrm{Hz}}{K_I}
\end{aligned}""",
# 11: solution 9, the gain limit
r"""\begin{aligned}
&\text{bisection on } \max|z| \text{ of the closed loop at the cruise point, } K_i \text{ fixed at } 125\ \%/(\mathrm{mm\,s}):\\
&K_{p,\max} = 897.5\ \mathrm{m^{-1}} = 89.8\ \%/\mathrm{mm},\qquad \text{crossover at the edge } 37.8\ \mathrm{Hz}\\
&K_{\mathrm{vel}} = K_p\cdot(\dot{y}\ \text{per unit}\ u) = K_p\cdot 0.246\ \mathrm{m/s}:\quad 61.5\ \mathrm{s^{-1}}\ \text{(default)},\quad 220.8\ \mathrm{s^{-1}}\ \text{(edge)}\\
&\text{rule } K_{\mathrm{vel}} < 2\zeta_h\omega_h,\ \text{ram mode } 87.9\ \mathrm{Hz},\ \zeta_h = 0.26:\quad 2\cdot0.26\cdot552 = 286.8\ \mathrm{s^{-1}} \quad\Rightarrow\quad K_p = 116.6\ \%/\mathrm{mm}
\end{aligned}""",
]

IDEAL = [
r"""A_1x_1 = A_2x_2 \quad\Rightarrow\quad x_2 = r\,x_1,\qquad r = \frac{A_1}{A_2} = \left(\frac{d_1}{d_2}\right)^2""",
r"""F_2 = p\,A_2 = F_1\,\frac{A_2}{A_1}""",
r"""F_1x_1 = p\,A_1x_1 = p\,A_2x_2 = F_2x_2""",
r"""\begin{aligned}
T &= \tfrac12m_1\dot{x}^2 + \tfrac12(m_2 + M)(r\dot{x})^2 + \tfrac12\rho A_1h_1\dot{x}^2\\
&\quad + \tfrac12\rho A_pL_p\left(\frac{A_1}{A_p}\dot{x}\right)^2 + \tfrac12\rho A_2h_2(r\dot{x})^2 = \tfrac12\,\mu(x)\,\dot{x}^2\\
\mu(x) &= m_1 + (m_2 + M)\,r^2 + \rho A_1\left[(H_0 - x) + r\,(H_0 + rx) + L_p\,\frac{A_1}{A_p}\right]
\end{aligned}""",
r"""V(x) = -m_1g\,x + (m_2 + M)\,g\,r\,x + \tfrac12\rho gA_1(1 + r)\,x^2""",
r"""\begin{aligned}
&\frac{d}{dt}\frac{\partial T}{\partial\dot{x}} - \frac{\partial T}{\partial x} + \frac{\partial V}{\partial x} = F_1(t)\\
\Rightarrow\quad &\mu(x)\,\ddot{x} + \tfrac12\,\mu'\dot{x}^2 = F_1(t) - V'(x),\qquad \mu' = \frac{d\mu}{dx} = \rho A_1(r^2 - 1)
\end{aligned}""",
r"""\begin{aligned}
m_1a &= F_1 + m_1g - p_1A_1 &&\Rightarrow\quad p_1 = \frac{F_1 + m_1g - m_1a}{A_1}\\
(m_2 + M)\,r\,a &= p_2A_2 - (m_2 + M)\,g &&\Rightarrow\quad p_2 = \frac{(m_2 + M)(g + ra)}{A_2}
\end{aligned}""",
r"""\begin{array}{lll}
\text{bottom of left column} & p_{b1} = p_1 + \rho(g - a)\,h_1 & \text{weight of the column, less what its downward acceleration needs}\\
\text{pipe inlet} & p_{\mathrm{in}} = p_{b1} + \tfrac12\rho\left(v^2 - v_p^2\right) & \text{Bernoulli: speeding the oil up costs pressure}\\
\text{pipe outlet} & p_{\mathrm{out}} = p_{\mathrm{in}} - \rho\,\dfrac{A_1}{A_p}\,a\,L_p & \text{the force that accelerates the oil plug in the pipe}\\
\text{bottom of right column} & p_{b2} = p_{\mathrm{out}} + \tfrac12\rho\left(v_p^2 - r^2v^2\right) & \text{slowing down gives the pressure back (lossless here)}\\
\text{top of right column} & p_{b2} - \rho(g + ra)\,h_2 = p_2 & \text{must agree with the output piston}
\end{array}""",
]
