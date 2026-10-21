# Task: publish the hydraulics study as a portfolio piece on my personal website

You are working in two repositories and with Cloudflare. Work in small, checked steps. Before anything hard to undo, tell me exactly what you will do and wait for my yes. That covers merging, deploying to production, changing DNS, deleting files and force-pushing.

## The source: numa1997/gergi-s-vision, branch `main`
Three finished, self-contained HTML pages. Each has everything inline (CSS, JS and fonts as base64), loads nothing from the network and has no build step at runtime:

| file | what it is | size |
|---|---|---|
| `hydraulic.html` | Ideal Hydraulic Press: one-coordinate Lagrangian, animated to scale, pressure probe | ~0.65 MB |
| `hydraulic_control.html` | Servo-Hydraulic Press: 8-state nonlinear model, digital PID, valve cutaway, Bode/Nyquist/z-plane; runs a Web Worker from a blob URL | ~1.0 MB |
| `hydraulic_theory.html` | Hydraulics from First Principles: a 23-chapter textbook, KaTeX pre-rendered, fonts embedded | ~2.6 MB |

Supporting files:
- **Theory build:** `theory/*.src.html`, `tools/build_theory.py`, `tools/theory_template.html`. Rebuild with `cd tools && npm install`, then `python3 tools/build_theory.py`.
- **Interactive pages' equations:** `tools/render_page_math.py` and `tools/page_equations.py`, which use the same KaTeX install.
- **Verification:** `check_physics.py` and `check_control.py`. Both must still print `ALL CHECKS PASSED` after any change that touches the physics.
- **Licences:** `fonts/LICENSE-fonts.txt` (OFL for the text fonts, MIT for the KaTeX fonts). It must travel with the pages.
- **Cross-links:** the pages link to each other with relative hrefs (`hydraulic.html`, `hydraulic_control.html`, `hydraulic_theory.html`). Keep the three files in one folder so the links keep working. Do **not** use `tools/make_artifact.py`; that was for a different host.

## The target: <WEBSITE_REPO>, the portfolio section
1. **Explore first and report before changing anything.** Find the framework and how the portfolio section works: where entries live, their format (Markdown, MDX, JSON or components), the fields a card needs (title, summary, thumbnail, tags, date, link), and how static files are served. Then propose a plan and wait for my yes.
2. **Add the pages as static files.** Put the three HTML files, unmodified, under a path such as `/portfolio/hydraulics/`, served exactly as they are. Do not run them through the site's bundler, minifier or HTML transforms. Inline scripts, data-URI fonts and the blob Web Worker must survive.
3. **Add one portfolio entry,** in the site's own style, with:
   - Title: "Hydraulics, from Pascal to a servo loop".
   - A two-sentence summary, written in my voice.
   - Tags: physics, simulation, control, hydraulics.
   - A link to the theory page and to each of the two simulations.
   - A thumbnail: a real screenshot of the servo press. Take it with Playwright (Chromium at `/opt/pw-browsers/chromium` if present), and size it to what the site's cards use.
4. **Match the site's navigation.** If the site expects a way back to the portfolio, add a small "← Portfolio" link to each page. Make it the only edit to the HTML, and show me the diff first.

## Cloudflare
1. **Find out how the site deploys.** Pages (Git integration, or Wrangler direct upload) or Workers static assets. Read the existing config (`wrangler.toml` / `wrangler.jsonc`, the Pages project settings) before changing it.
2. **Check the limits and headers.**
   - The largest file is ~2.6 MB, inside Cloudflare's per-file limit (25 MiB), but confirm against current Cloudflare documentation.
   - Make sure no `_headers` rule or CSP blocks inline scripts, `data:` fonts, or `blob:` workers on `/portfolio/hydraulics/*`. If one would, propose a scoped header rule.
   - Make sure HTML is served as `text/html; charset=utf-8`.
3. **Deploy a preview first** (preview branch or preview deployment) and give me the URL. Production happens only after I say yes.
4. **Do not touch DNS, domains or other projects** unless I ask.

## Verify before you tell me it is done
On the preview URL, at 360, 390, 1024 and 1440 px wide:
- **Console:** no errors on any of the three pages.
- **Layout:** no horizontal page scroll.
- **Control page:** the status line reads "Computed in … s in the background" (the Web Worker ran), and the Bode plot draws.
- **Theory page:** the equations render as typeset math (`.katex` elements present, no raw `$`).
- **Links:** the three pages link to each other, and the portfolio card links to them.

Report with evidence: the commands you ran, their output, and screenshots. Mark each statement as fact (verified, with its handle), inference, or opinion.

## Git
- **Branches:** work on a new branch in each repository and never push to main directly.
- **PRs:** open a pull request in the website repository with the plan, the diff summary and the preview URL. Use the repository's PR template if it has one.
- **Commits:** write clear, descriptive commit messages.
