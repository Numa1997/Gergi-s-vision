# Hydraulic Press Study

> **Moved.** Since 21 October 2026 this study lives in the website repository, [`Numa1997/SiteTest`](https://github.com/Numa1997/SiteTest), folder `portfolios-src/hydraulics/`, and is served at <https://phyeinusul.com/portfolios/hydraulics/index.html>. This repository is no longer updated.

From Pascal's principle to a digitally controlled servo-hydraulic press: two simulations you can run and
play with, and a 23-chapter textbook that derives every equation they integrate.

**Start with `hydraulics.html`.** It is the whole study in one file, with one tab per page:

| tab | standalone page | what it is |
|---|---|---|
| Servo press | `hydraulic_control.html` | Pump, four-way servo valve (drawn in section), 2 m of hose, differential cylinder and specimen under a digital PID controller sampled every 1 ms. Eight-state nonlinear model, RK4, energy audit to 1e-14; gauges, time plots, Bode / Nyquist / z-plane loop analysis, nine worked solutions. Press ▶ Play; every slider recomputes the cycle. |
| Ideal press | `hydraulic.html` | Pascal's press from a one-coordinate Lagrangian, drawn to scale, with a pressure probe in the oil. |
| Theory | `hydraulic_theory.html` | *Hydraulics from First Principles*: 23 chapters, 63 numbered equations, 8 figures, every formula typeset with KaTeX at build time, every "In our press" number computed from the models. |

Every page is a single self-contained file: CSS, JavaScript and fonts are inline, nothing is loaded from the
network except, for `hydraulics.html`, two Google Fonts faces for its tab bar (with system fallbacks).
Open any of them straight from disk. The standalone pages link to each other by relative file name, so
keep them in one folder; inside `hydraulics.html` those same links switch tabs.

## How `hydraulics.html` is put together

`tools/build_combined.py` embeds the three standalone pages unchanged, each as a JSON string, and shows each
in its own frame (`srcdoc`, with a `blob:` fallback), so their styles, ids and scripts cannot collide. A
small script added to each embedded page turns links between the pages into tab switches and keeps
in-page `#` links working. `#servo`, `#ideal` and `#theory` open a tab directly.

Needs from a host: inline scripts, `'unsafe-eval'` (the servo page builds its background Web Worker with
`new Function`), `blob:` workers, `data:` fonts, `srcdoc` frames. Served as `text/html; charset=utf-8`.

## Rebuilding

The two simulation pages are edited directly; they are their own source. The rest is generated:

```sh
(cd tools && npm ci)                 # KaTeX 0.16.11, once
python3 tools/build_theory.py        # theory/*.src.html -> hydraulic_theory.html
python3 tools/render_page_math.py    # typesets the equation blocks inside the two simulation pages
python3 tools/build_combined.py      # the three pages -> hydraulics.html (run this last)
```

For the website, phyeinusul.com, `python3 tools/build_combined.py --site <path to a SiteTest clone>` writes
`public/portfolios/hydraulics/index.html` there. It is the same page, with the site's security policy (plus
`'unsafe-eval'` and `blob:` workers, which the servo page needs), the site's own fonts instead of Google
Fonts, and a link back to the Portfolios page.

From a clean clone these reproduce the committed files byte for byte.

## Checks

| command | what it proves |
|---|---|
| `python3 check_physics.py` | The ideal press's JavaScript physics agrees with an independent Python model. |
| `python3 check_control.py` | The servo press's equilibria, linearization, discretization, closed-loop poles, margins, nonlinear cycle and energy audit agree with an independent SciPy/SymPy model. |
| `node tools/check_theory_numbers.js hydraulics.html` | Every number the theory quotes is what the models embedded in `hydraulics.html` compute. |
| `python3 tools/check_combined.py` | In a real browser: each tab holds everything its standalone page has; Play, sliders, links, tabs and deep links work; no script errors; nothing scrolls sideways at 360–1440 px. |

All four must pass after any change. The browser check needs Playwright for Python and Chromium.

## Files

- `theory/*.src.html`: the textbook's source, HTML with LaTeX math. `tools/theory_template.html` is its page.
- `tools/page_equations.py`: the TeX of the equation blocks on the two simulation pages.
- `fonts/`: IBM Plex Sans, IBM Plex Mono and Instrument Serif (SIL OFL 1.1) as embedded in the pages, and
  `LICENSE-fonts.txt`, which also covers the embedded KaTeX fonts (MIT). It must travel with the pages.
- `dump_runs.js`, `dump_control.js`: run the pages' physics blocks in Node; used by the check scripts.
- `tools/make_artifact.py`: prepares a page for the claude.ai Artifact host. Not needed elsewhere.
- `tools/assemble_control.py`, `tools/assemble_ideal.py`: historical. They assembled the first versions of
  the two simulation pages from drafts that are not in the repository and cannot be rerun.
- `MIGRATION_PROMPT.md`: instructions for publishing the study on the personal website.
