# Task: put the Hydraulic Press Study on my website, phyeinusul.com, as Portfolio project 03

You will work in **two GitHub repositories** and deploy to **Cloudflare**:

| | Repository | Your role there |
|---|---|---|
| **Source** | `Numa1997/Gergi-s-vision`, branch `main` | Clone it, run its checks, and generate the website copy of the study. Change it only if something must change at the source; if so, work on a branch and open a PR. |
| **Website** | `Numa1997/SiteTest`, branch `main` | Add the study and its Portfolio entry on a new branch, open a PR, deploy a preview to Cloudflare, and after my yes merge and deploy to production. |

**The end result I want to see:** on <https://phyeinusul.com/portfolios.html>, a third project, **03**, below
01 Droplet Collection and 02 Rotor Pendula, in exactly their style. Its buttons open the study at
<https://phyeinusul.com/portfolios/hydraulics/index.html>, which works there exactly as it does in the source
repository. The home page's "Research projects" paragraph mentions it too.

## How to work with me

- **Before anything hard to undo, ask and wait for my explicit yes.** That covers:
  - merging;
  - `npx wrangler deploy` (it publishes to production straight away);
  - any change to Cloudflare settings, DNS, routes or domains;
  - deleting or renaming files;
  - force-pushing.

  A yes covers only the action it names.
- **Read `CLAUDE.md` and `AGENTS.md` in the website repository first and follow them.** They are my rules
  for that repository. Among them:
  - talk plainly;
  - build, test in a real browser, show screenshots, commit;
  - a change is not done until the docs that describe the changed files say what the code now does.
- **Label what you tell me** as *fact* (with the command, the file and line, or the URL I can check),
  *inference* or *opinion*. Never pass one off as another.
- **Metric units.** I have a BSc in physics: define jargon the first time you use it.
- **Ask only what you cannot find out yourself, one question at a time.** Never ask me to paste a secret
  into the chat.

## What is already known (facts, checked on 21 October 2026)

**The website** (from `SiteTest/README.md`, `docs/usul.md`, `wrangler.jsonc` and `docs/portfolios.md`):

- **Phyein Usul**, live at <https://phyeinusul.com>; `www.phyeinusul.com` and
  `phyein-usul.phyeinusul.workers.dev` serve the same files.
- It is a Cloudflare **Worker with static assets only**, named `phyein-usul`, on the Free plan.
- **Build and deploy:** `npm install && npm run build` (Vite, `index.html` + `public/` → `dist/`), then
  `npx wrangler deploy`. Nothing deploys automatically from GitHub: the deploy is that command, run by
  hand, and it needs a Cloudflare sign-in.
- **The Portfolios page** is `public/portfolios.html`, and each project on it is an
  `<article class="proj" id="…">`. Each article has:
  - a band with its number, a context line and its fields;
  - a title, a subtitle and an abstract;
  - action buttons: one "Open the project", the rest "ghost" buttons into the project's own views;
  - a tally of four key figures;
  - four numbered parts (`2.1`…`2.4`): the answer, what changed, four figures as plates, and the project's
    own pages.
- **Project copies** live in `public/portfolios/<name>/`, carry the site's security policy right after the
  charset line, use the site's self-hosted fonts (no Google Fonts), end their title in "· Numa Koudsie",
  and link back with "← Numa Koudsie · Portfolios" to `../../portfolios.html`.
- **Two security layers apply to every page.** `public/_headers` sends response headers for `/*`:
  `X-Frame-Options: SAMEORIGIN`, COOP `same-origin`, and a CSP limited to `frame-ancestors`, `object-src`,
  `base-uri` and `form-action`. Each page also carries its own `<meta>` Content-Security-Policy (see
  `docs/build-and-deploy.md`, "Security").
- **The docs** that describe the Portfolios page and the copies and say "two research projects": `README.md`
  (lines 4 and 23), `docs/portfolios.md`, `docs/pages.md`, `docs/files.md`, `docs/architecture.md`. The
  home page's paragraph is in `index.html`, section `#research`.

**The study** (from `Gergi-s-vision/README.md`):

- One self-contained HTML file with three tabs:
  - **Servo press:** the animated servo-hydraulic press with its digital controller; it opens first;
  - **Ideal press:** Pascal's press;
  - **Theory:** a 23-chapter textbook that derives every equation.

  `#servo`, `#ideal` and `#theory` open a tab directly.
- **The website copy is generated, not hand-edited:**

  ```sh
  python3 tools/build_combined.py --site <path to the SiteTest clone>
  ```

  This writes `public/portfolios/hydraulics/index.html` (5.1 MB) and `LICENSE-fonts.txt` beside it. The
  copy follows the site's rules:
  - the site's policy and referrer rule are taken from `SiteTest/index.html`;
  - the site's fonts (`../../fonts/instrument-plex.css`);
  - the title "Hydraulic Press Study · Numa Koudsie";
  - the back link.
- **The copy's policy needs two additions** to the site's policy, because the servo page starts its
  background solver (a Web Worker) from a `blob:` URL and builds it with `new Function`:
  - `'unsafe-eval'` in `script-src`;
  - `blob:` in `worker-src`.

  They apply only inside this one page, since a `<meta>` policy governs only the page that carries it. Tell
  me about them in the PR. Do not change the other pages' policies.
- **Already verified** with the copy served from a local clone of `SiteTest` (`python3 -m http.server` in
  `public/`), under the site's policy:
  - all 33 browser checks pass;
  - all 52 theory-number checks pass;
  - the page makes no request outside the site;
  - the fonts are the site's own.

  The only 404 was `/favicon.ico`, which the site lacks for every page; the browser asks for it on its own.

## Step 1: confirm the ground (read-only)

1. Clone both repositories.
2. In the source repository, run its four checks. All must pass:

   ```sh
   (cd tools && npm ci)
   python3 check_physics.py
   python3 check_control.py
   node tools/check_theory_numbers.js hydraulics.html       # ALL 52 THEORY NUMBERS MATCH THE MODELS
   python3 tools/check_combined.py                          # ALL 33 BROWSER CHECKS PASSED
   ```

   Use Playwright with Chromium at `/opt/pw-browsers/chromium` if it exists.
3. In the website repository, read `CLAUDE.md`, `AGENTS.md`, `docs/usul.md`, `docs/portfolios.md`,
   `docs/pages.md` and `public/portfolios.html`.
4. Check that the facts above still hold, and tell me anything that differs.
5. Find out how your session can reach Cloudflare: a `CLOUDFLARE_API_TOKEN` in the environment, a
   `wrangler login`, or Cloudflare MCP tools. If it can't, tell me exactly what you need.

Report in a few lines and wait for my yes.

## Step 2: add the study to the website (new branch in `SiteTest`)

1. **The page.** Run `python3 tools/build_combined.py --site <SiteTest clone>` from the source repository.
   Do not edit the generated file. If something in it must change, change the generator in the source
   repository (branch + PR there), rerun the four checks, and regenerate.
2. **Article 03** in `public/portfolios.html`, after 02, built from exactly the same markup and classes as
   01 and 02, with `id="hydraulic-press"`:
   - **Band:**
     - number `03`;
     - context line, a draft: "An interactive study · from first principles · 2026";
     - fields: "fluid mechanics · control engineering · numerical simulation".
   - **Title:** "Hydraulic Press Study". **Subtitle,** a draft: "How a digital controller makes 12 MPa of
     oil press a specimen with 60 kN, and hold it."
   - **Abstract:** in my voice, the same length and register as the other two; show me a draft. It should
     say what you see and can do:
     - a servo-hydraulic press (pump, four-way servo valve, 2 m of hose, differential cylinder and
       specimen) under a PID controller sampled every 1 ms;
     - press Play, move any slider, and the whole cycle is recomputed;
     - Bode, Nyquist and z-plane plots show whether the loop survives;
     - Pascal's ideal press as the starting point;
     - a 23-chapter companion text derives every equation the animation integrates;
     - every number in it is checked against the model.
   - **Buttons:**
     - "Open the project" → `portfolios/hydraulics/index.html#servo`;
     - ghost "Read the derivations" → `#theory`;
     - ghost "Start from Pascal" → `#ideal`.
   - **Tally,** four key figures, taken from the page's own numbers (the chips under the servo page's title,
     and the theory). Suggested:
     - 63.6 kN, peak force for a 60 kN target;
     - 64° · 11.0 dB, the position loop's phase and gain margins;
     - 93 %, the share of the pump's work the valve turns into heat;
     - 1 ms, the controller's sample time.

     Re-read each from the page before you use it.
   - **Parts 3.1–3.4,** like the others:
     - 3.1, the answer in a few lines;
     - 3.2, what the model includes;
     - 3.3, four figures as plates, each linking into the study;
     - 3.4, the study's own pages: Servo press, Ideal press, Theory, each with one line.

     For 3.3 the other projects use SVG figures. Here, make PNG screenshots with Playwright, sized like the
     other plates (300 px high, their width): the press mid-cycle, the time plots, the Bode/Nyquist/z-plane
     row, and the theory's map of the machine (chapter 0). Store them in `public/portfolios/hydraulics/fig/`.
     Show me them.
3. **The home page.** In `index.html`, section `#research`, add the study to the sentence that lists the
   projects on the Portfolios page.
4. **The docs.** Update every place that says "two research projects" or describes the copies:
   - `README.md`;
   - `docs/portfolios.md`: a section on the study, which is generated by
     `Gergi-s-vision/tools/build_combined.py --site`, is not an AppDeploy build, has its own policy
     additions and why, and how to update it;
   - `docs/pages.md`;
   - `docs/files.md`, with sizes;
   - `docs/architecture.md`.
5. **Build and test locally:**
   - Run `npm run build`.
   - Prove the study is copied unchanged into `dist/portfolios/hydraulics/index.html`: compare SHA-256
     checksums with the generated file.
   - Serve `dist/` and run `python3 tools/check_combined.py http://localhost:<port>/portfolios/hydraulics/index.html`
     from the source repository. It must report ALL 33 PASSED.
   - Check the Portfolios page in a real browser at 360, 390, 1024 and 1440 px: the article looks like its
     neighbours, every link works, the console is clean (the favicon aside), and nothing scrolls sideways.
     Screenshots, please.
6. Commit with clear messages, push the branch, and open a PR with:
   - what changed;
   - the policy additions and why;
   - the check results;
   - the screenshots.

## Step 3: a preview on Cloudflare (only after my yes)

Production must not change at this step. Propose how to get a preview URL, and check the command against
Cloudflare's current Workers documentation; link it. For a Worker with `workers_dev: true`, `npx wrangler
versions upload` uploads a version and gives a preview URL without deploying it. On the preview:

- run `python3 tools/check_combined.py <preview URL>/portfolios/hydraulics/index.html`;
- download the served file and run `node tools/check_theory_numbers.js <file>`;
- compare the SHA-256 of the served file with the generated one;
- show me the response headers (`content-type: text/html; charset=utf-8`).

## Step 4: production (only after my explicit yes)

1. Merge the PR into `main`.
2. Run `npx wrangler deploy` from `main`.
3. Repeat the Step 3 checks on <https://phyeinusul.com/portfolios/hydraulics/index.html> and on the
   Portfolios page.
4. Report with evidence.

Do not touch DNS, the custom domains, the zone's settings, other Workers or the AppDeploy app
`numa-koudsie-website-0cyj78` (it stays as it is unless I ask).

## Git

- Work on a new branch in each repository you change. Never push to `main` directly; merge only after my
  yes.
- Use each repository's PR template if it has one.
- Write clear, descriptive commit messages.
