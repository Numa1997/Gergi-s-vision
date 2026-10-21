# Task: publish the Hydraulic Press Study in the portfolio section of my personal website

You will work in two GitHub repositories and in my Cloudflare account. The goal is a new entry in the
**portfolio section of my personal website**, next to the other projects already there. The website lives
on a subdomain served by Cloudflare. The entry opens the Hydraulic Press Study, which must work there
exactly as it does in the source repository.

## How to work with me

- **Ask before anything hard to undo,** and wait for my explicit yes. That covers merging, deploying to
  production, changing DNS, routes or domains, changing Cloudflare zone or project settings, deleting or
  renaming files, and force-pushing. A yes covers only the action it names.
- **One step at a time.** After each step, tell me in a few lines where we are and what you propose next.
  Ask at most one question at a time.
- **Label what you tell me:** *fact* (verified, with the command, file and line, or URL I can check),
  *inference* (your reasoning from facts) or *opinion* (your judgement). Never pass one off as another.
- **When there is a real choice,** give me 2–3 options, each with its main cost and its main risk, then your
  pick, marked as your opinion.
- **Never guess about my accounts:** repository names, domains, the Cloudflare account, plans, tokens. Ask.
  "I don't know" is an acceptable answer, followed by how to find out.
- **Units are metric.** I have a BSc in physics, so define jargon the first time you use it.

## The source: `Numa1997/Gergi-s-vision`, branch `main` (commit `f0942b3` or later)

Read `README.md` first. In short:

| file | what it is | size |
|---|---|---|
| `hydraulics.html` | **The deliverable.** The whole study in one file, one tab per page: Servo press (opens first), Ideal press, Theory. `#servo`, `#ideal` and `#theory` open a tab directly. | 5.1 MB |
| `hydraulic_control.html` | The servo-hydraulic press on its own: animation, gauges, sliders, time plots, Bode / Nyquist / z-plane, worked solutions. Runs a Web Worker from a `blob:` URL. | 1.0 MB |
| `hydraulic.html` | The ideal press on its own. | 0.65 MB |
| `hydraulic_theory.html` | *Hydraulics from First Principles*, the 23-chapter textbook, KaTeX pre-rendered. | 2.6 MB |
| `fonts/LICENSE-fonts.txt` | Licences for the embedded fonts (SIL OFL 1.1, and MIT for KaTeX). **Must be published with the pages.** | |

`hydraulics.html` contains the other three pages verbatim, so it is self-sufficient. Publish the
standalone pages next to it anyway, in the same folder: they are direct links to each part, and they link
to each other by relative file name (`hydraulic.html`, `hydraulic_control.html`, `hydraulic_theory.html`).

**What the pages need from the host** (fact: `README.md`, "How hydraulics.html is put together"):

- inline `<script>` and `<style>`;
- `'unsafe-eval'`, because the servo page builds its background Web Worker with `new Function`;
- `worker-src blob:`;
- `data:` fonts;
- `srcdoc` frames, with `blob:` frames as the fallback;
- for the tab bar of `hydraulics.html` only: Google Fonts (`fonts.googleapis.com` and `fonts.gstatic.com`),
  with system fonts as the fallback;
- served as `text/html; charset=utf-8`;
- **byte for byte unchanged**: no bundler, no minifier, no HTML rewriting.

**The checks** (run them from a clone of the source repository; all four must pass before and after):

```sh
(cd tools && npm ci)
python3 check_physics.py                                 # ideal press physics vs an independent model
python3 check_control.py                                 # servo press physics vs an independent model
node tools/check_theory_numbers.js hydraulics.html       # 52 numbers in the theory vs the models
python3 tools/check_combined.py [file-or-URL]            # the page in a real browser: 33 checks
```

`tools/check_combined.py` takes a URL as well as a file, and the standalone pages it compares against are
read from the local clone. It needs Playwright for Python; use Chromium at `/opt/pw-browsers/chromium` if
it exists. **Do not use** `tools/make_artifact.py`: it is for a different host.

## Step 1: the target repository, explore and report (read-only)

My website is a GitHub repository. **I believe it is `Numa1997/SiteTest`, but confirm that with me before
you read or change anything in it.** Once confirmed, find out and report:

1. **The framework** and its build: Astro, Next, Hugo, plain HTML, …; the build command and output folder.
2. **The portfolio section:**
   - where its entries live, and their format (Markdown/MDX front matter, JSON, YAML, components);
   - every field an entry uses (title, summary, date, tags, thumbnail, link, order, featured, …);
   - how the other projects present themselves: a card linking out, a detail page with a link,
     or an embedded page.
   
   Show me two existing entries as examples. The new entry must look like them.
3. **Static files:** how they are served (`public/`, `static/`, …). Check whether the build touches HTML
   there: minification, link rewriting, trailing slashes, "pretty URLs".
4. **How the site deploys to Cloudflare:**
   - Pages with Git integration, Pages via Wrangler direct upload, or Workers static assets;
   - the project name, the production branch, the preview branches;
   - the custom domain or subdomain.
   
   Read `wrangler.toml` / `wrangler.jsonc`, any `_headers`, `_redirects`, Functions or middleware, and the
   Pages project settings. **Read only; change nothing.**
5. **Anything that would break the pages:**
   - a Content-Security-Policy from `_headers`, a `<meta>` tag or middleware that blocks the needs listed
     above;
   - Cloudflare features that rewrite HTML or scripts. **Rocket Loader** rewrites `<script>` tags and
     **must be off** for these pages. Also check Email Address Obfuscation, any HTML minification still
     in place, and Zaraz injections.

   Check the zone settings with read access only.
6. **Size limits:** confirm the current per-file limit for the deploy method from Cloudflare's
   documentation (link it). It has been 25 MiB per file for Pages and for Workers static assets; the
   largest file here is 5.1 MB.

Then propose a plan, with options where there are real choices, and **wait for my yes**.

## Step 2: add the study (on a new branch in the website repository)

1. **Files.** Copy unchanged into one folder of the site's static files, for example
   `/portfolio/hydraulics/` (choose the path to match how the other projects are laid out, and tell me):
   `hydraulics.html`, `hydraulic_control.html`, `hydraulic.html`, `hydraulic_theory.html`, and
   `LICENSE-fonts.txt`.
   - Ask me whether the entry URL should be the folder itself (then `hydraulics.html` is also copied as
     `index.html` in it) or `…/hydraulics.html`.
   - Prove the files are unchanged: compare SHA-256 checksums between the source repository and the build
     output, and show me the comparison.
2. **The portfolio entry,** in exactly the format and style of its neighbours:
   - **Title:** "Hydraulic Press Study", or "Hydraulics, from Pascal to a servo loop" if the neighbours'
     titles are descriptive. Show me both in context.
   - **Summary:** two sentences in my voice, for me to approve. A draft: *"A servo-hydraulic press under
     digital control, simulated from first principles: pump, servo valve, hose, cylinder and a 1 ms PID
     loop, with Bode, Nyquist and z-plane analysis you can play with. A 23-chapter companion text derives
     every equation the animation integrates, from Pascal's principle up."*
   - **Tags:** physics, simulation, control, hydraulics, or whatever the site's own tag vocabulary has for
     these.
   - **Date:** October 2026.
   - **Main link:** the study, opening on the servo press (`…#servo`). If the format allows extra links:
     Ideal press (`#ideal`) and Theory (`#theory`).
   - **Thumbnail:** a real screenshot of the servo press tab, taken with Playwright, with the press
     mid-cycle (press ▶ Play, wait about 2 s). Use the same size, aspect ratio, format and compression as
     the other thumbnails. Show it to me.
3. **The way back.** If the other projects have a link back to the portfolio, the study needs one too.
   - **Do not hand-edit the pages.** The right place is the tab bar of `hydraulics.html`. Propose a small
     change to `tools/build_combined.py` in the **source** repository, for example an optional
     `--back-link URL` argument that adds a "← Portfolio" link to the header.
   - Do it on a branch there, rebuild, rerun all four checks, and open a PR there.
   - Show me the diff first.

## Step 3: deploy a preview

Deploy a preview (a preview branch or a preview deployment, never production) and give me its URL. Then
verify on the preview, and show the evidence:

- `python3 tools/check_combined.py <preview URL of the study>` gives **ALL 33 BROWSER CHECKS PASSED**.
- Download the deployed `hydraulics.html` and run `node tools/check_theory_numbers.js <downloaded file>`;
  it must give **ALL 52 THEORY NUMBERS MATCH THE MODELS**.
- The SHA-256 of each deployed page (fetched with `curl`) equals the source file's. If they differ,
  something rewrote the HTML: find what, and stop.
- The response headers: `content-type: text/html; charset=utf-8`, and no CSP that blocks the needs above.
  Show me the headers.
- The portfolio page on the preview, at 360, 390, 1024 and 1440 px wide:
  - the new card sits with the others and looks like them;
  - its links open the right tab;
  - nothing scrolls sideways;
  - the browser console is clean.
  
  Screenshots, please.
- The standalone pages open, and their links to each other work.

## Step 4: production, only after my explicit yes

- Merge the website PR, or promote the preview deployment, only when I say so.
- Repeat the Step 3 checks on the production URL.
- **Do not touch** DNS, routes, custom domains, other Cloudflare projects or other zones unless I ask.

## Git

- Work on a new branch in each repository. Never push to `main` directly.
- Open a PR in the website repository containing:
  - the plan;
  - a summary of the diff;
  - the preview URL;
  - the check results.
  
  Use the repository's PR template if it has one.
- Write clear, descriptive commit messages.

## What I don't know yet, and you should ask me rather than assume

- Which repository is the website (I think `Numa1997/SiteTest`), and which subdomain serves it.
- How the Cloudflare account is reached from your session: an API token in the environment, `wrangler`
  login, or the Cloudflare MCP tools. If you lack access, say exactly what you need, and never ask me to
  paste a secret into the chat.
- Whether portfolio entries should open the project in the same tab or a new one, if the site doesn't
  already decide that.
