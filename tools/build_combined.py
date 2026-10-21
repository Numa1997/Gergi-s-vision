#!/usr/bin/env python3
"""Build hydraulics.html: the three pages in one file, one tab each.

The servo press, the ideal press and the theory page are embedded unchanged, each as a JSON string, and
each runs in its own frame, so their styles, element ids and scripts cannot collide. A small script added
to each page turns the links between the pages into tab switches and keeps in-page links (#...) working
inside the frame.

Usage: python3 tools/build_combined.py            -> hydraulics.html (a complete document)
       python3 tools/build_combined.py --artifact out.html
                                                    -> the same without doctype/html/head/body, for hosts
                                                       that add their own skeleton
"""
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
PAGES = [  # tab id, file, tab label, short label for phones
    ('servo', 'hydraulic_control.html', 'Servo press', 'Servo'),
    ('ideal', 'hydraulic.html', 'Ideal press', 'Ideal'),
    ('theory', 'hydraulic_theory.html', 'Theory', 'Theory'),
]
FILE_TO_TAB = {f: t for t, f, _, _ in PAGES}

# Added to the end of each embedded page. It talks to the shell only through postMessage.
BRIDGE = '''<script>
(function () {
  var TAB = %(tab)s, FILES = %(files)s;
  function scrollToId(id) {
    var t = id && document.getElementById(id);
    if (!t) return false;
    var smooth = !window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    t.scrollIntoView({ behavior: smooth ? 'smooth' : 'auto', block: 'start' });
    return true;
  }
  document.addEventListener('click', function (e) {
    var a = e.target.closest && e.target.closest('a[href]');
    if (!a) return;
    var h = a.getAttribute('href');
    if (h.charAt(0) === '#') {
      if (h.length > 1) { e.preventDefault(); scrollToId(decodeURIComponent(h.slice(1))); }
      return;
    }
    var parts = h.split('#'), tab = FILES[parts[0]];
    if (tab) { e.preventDefault(); parent.postMessage({ hydraulicsGoto: tab, frag: parts[1] || '' }, '*'); return; }
    if (/^https?:/.test(h)) { a.target = '_blank'; a.rel = 'noopener'; }
  }, true);
  window.addEventListener('message', function (e) {
    var d = e.data;
    if (d && typeof d.hydraulicsFrag === 'string') scrollToId(d.hydraulicsFrag);
  });
  parent.postMessage({ hydraulicsReady: TAB }, '*');
})();
</script>
'''

SHELL = r'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Hydraulic Press Study</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;600&family=Instrument+Serif&display=swap">
<style>
/* The three pages share one warm paper look and have no dark variant, so the shell commits to it too. */
:root {
  --paper: #efe6d6; --panel: #f8f2e7; --ink: #2b2420; --muted: #6e6257; --line: #d8cab4;
  --oil: #7a1f2b; --oil-ink: #fff8f0; --focus: #2f5d7c;
  color-scheme: light;
}
html, body { height: 100%%; }
body {
  margin: 0; background: var(--paper); color: var(--ink);
  font: 15px/1.4 'IBM Plex Sans', system-ui, -apple-system, 'Segoe UI', sans-serif;
  display: flex; flex-direction: column; overflow: hidden;
  height: calc(100dvh - env(safe-area-inset-top, 0px) - env(safe-area-inset-bottom, 0px));
}
header {
  display: flex; align-items: center; gap: 12px 20px; flex-wrap: wrap;
  padding-block: 10px; padding-left: max(16px, env(safe-area-inset-left, 0px));
  padding-right: max(16px, env(safe-area-inset-right, 0px));
  background: var(--panel); border-bottom: 1.5px solid var(--line);
}
.brand { display: flex; flex-direction: column; min-width: 0; }
.brand b { font: 400 24px/1 'Instrument Serif', Georgia, serif; letter-spacing: .01em; }
.brand span { font-size: 11px; letter-spacing: .12em; text-transform: uppercase; color: var(--muted); margin-top: 3px; }
nav { display: flex; gap: 6px; margin-left: auto; }
nav button {
  font: 600 14px/1 'IBM Plex Sans', system-ui, -apple-system, sans-serif; color: var(--ink); background: transparent;
  border: 1.5px solid var(--line); border-radius: 999px; padding: 10px 16px; min-height: 40px; cursor: pointer;
}
nav button:hover { border-color: var(--oil); }
nav button[aria-selected="true"] { background: var(--oil); border-color: var(--oil); color: var(--oil-ink); }
nav button:focus-visible { outline: 2.5px solid var(--focus); outline-offset: 2px; }
nav .short { display: none; }
main { position: relative; flex: 1; min-height: 0; }
main iframe {
  position: absolute; inset: 0; width: 100%%; height: 100%%; border: 0; background: var(--paper);
  visibility: hidden;
}
main iframe.on { visibility: visible; }
.loading { position: absolute; inset: 0; display: grid; place-items: center; color: var(--muted); }
@media (max-width: 560px) {
  header { padding-block: 8px; gap: 8px; }
  .brand span { display: none; }
  .brand b { font-size: 20px; }
  nav { margin-left: 0; width: 100%%; }
  nav button { flex: 1; padding: 10px 8px; }
  nav .long { display: none; }
  nav .short { display: inline; }
}
</style>
</head>
<body>
<header>
  <div class="brand"><b>Hydraulic Press Study</b><span>from Pascal to a servo loop</span></div>
  <nav role="tablist" aria-label="Pages">
%(buttons)s
  </nav>
</header>
<main id="stage"><div class="loading" id="loading">Loading…</div></main>
%(data)s
<script>
(function () {
  var TABS = %(tabs)s, frames = {}, ready = {}, current = null;
  var stage = document.getElementById('stage');
  function html(tab) { return JSON.parse(document.getElementById('page-' + tab).textContent); }
  function frame(tab) {
    if (frames[tab]) return frames[tab];
    var f = document.createElement('iframe');
    f.title = document.getElementById('tab-' + tab).textContent.trim();
    f.srcdoc = html(tab);
    stage.appendChild(f);
    frames[tab] = f;
    // If this host refuses srcdoc frames, the page never reports in; fall back to a blob URL.
    setTimeout(function () {
      if (ready[tab]) return;
      f.removeAttribute('srcdoc');
      f.src = URL.createObjectURL(new Blob([html(tab)], { type: 'text/html' }));
    }, 8000);
    return f;
  }
  function show(tab, frag) {
    if (TABS.indexOf(tab) < 0) tab = TABS[0];
    var f = frame(tab);
    if (current !== tab) {
      TABS.forEach(function (t) {
        var b = document.getElementById('tab-' + t), on = t === tab;
        b.setAttribute('aria-selected', on ? 'true' : 'false');
        b.tabIndex = on ? 0 : -1;
        if (frames[t]) frames[t].classList.toggle('on', on);
      });
      current = tab;
      try { history.replaceState(null, '', '#' + tab); } catch (e) {}
    }
    if (frag) {
      if (ready[tab]) f.contentWindow.postMessage({ hydraulicsFrag: frag }, '*');
      else f.dataset.frag = frag;
    }
  }
  window.addEventListener('message', function (e) {
    var d = e.data || {};
    if (d.hydraulicsReady) {
      var tab = d.hydraulicsReady, f = frames[tab];
      ready[tab] = true;
      if (tab === current) document.getElementById('loading').hidden = true;
      if (f && f.dataset.frag) { f.contentWindow.postMessage({ hydraulicsFrag: f.dataset.frag }, '*'); delete f.dataset.frag; }
    }
    if (d.hydraulicsGoto) { show(d.hydraulicsGoto, d.frag); if (ready[current]) document.getElementById('loading').hidden = true; }
  });
  TABS.forEach(function (t, i) {
    var b = document.getElementById('tab-' + t);
    b.addEventListener('click', function () { show(t); if (ready[t]) document.getElementById('loading').hidden = true; });
    b.addEventListener('keydown', function (e) {
      var k = e.key === 'ArrowRight' ? 1 : e.key === 'ArrowLeft' ? -1 : 0;
      if (!k) return;
      var n = TABS[(i + k + TABS.length) %% TABS.length];
      show(n); document.getElementById('tab-' + n).focus();
    });
  });
  var start = (location.hash || '').slice(1);
  show(TABS.indexOf(start) >= 0 ? start : TABS[0]);
})();
</script>
</body>
</html>
'''


def embed(tab, file):
    src = (ROOT / file).read_text()
    bridge = BRIDGE % {'tab': json.dumps(tab), 'files': json.dumps(FILE_TO_TAB)}
    i = src.rfind('</body>')
    assert i > 0, f'{file}: no </body>'
    src = src[:i] + bridge + src[i:]
    # JSON with every '<' escaped cannot end the <script> element early or open a comment.
    text = json.dumps(src, ensure_ascii=False).replace('<', '\\u003c')
    return f'<script type="application/json" id="page-{tab}">{text}</script>'


def build():
    buttons = '\n'.join(
        f'    <button role="tab" id="tab-{t}" aria-selected="false">'
        f'<span class="long">{label}</span><span class="short">{short}</span></button>'
        for t, _, label, short in PAGES)
    return SHELL % {'buttons': buttons, 'data': '\n'.join(embed(t, f) for t, f, _, _ in PAGES),
                    'tabs': json.dumps([t for t, _, _, _ in PAGES])}


def strip_skeleton(src):
    for pat in [r'<!doctype html>\n', r'<html lang="en">\n', r'<head>\n', r'</head>\n', r'<body>\n',
                r'</body>\n', r'</html>\n?', r'<meta charset="utf-8">\n', r'<meta name="viewport"[^>]*>\n']:
        src = re.sub(pat, '', src, count=1)
    return src


if __name__ == '__main__':
    out = build()
    if len(sys.argv) == 3 and sys.argv[1] == '--artifact':
        out, path = strip_skeleton(out), pathlib.Path(sys.argv[2])
    else:
        path = ROOT / 'hydraulics.html'
    path.write_text(out)
    print('wrote', path, f'{len(out.encode()) / 1e6:.2f} MB')
