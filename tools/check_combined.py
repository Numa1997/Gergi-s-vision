#!/usr/bin/env python3
"""Browser check of hydraulics.html, the three pages in one.

  1. Complete: each tab holds everything its standalone page has (headings, canvases, figures, typeset
     formulas, sliders, buttons, links, tables), counted in a real browser.
  2. Working:  no script errors; the servo cycle computes with a closed energy audit; Play advances time
     on both presses; a slider change recomputes the servo cycle; the theory's contents links scroll;
     links between the pages switch tabs; #servo, #ideal and #theory open the right tab; the plots draw.
  3. Layout:   no sideways scrolling of the page or of any tab at 360, 390, 1024 and 1440 px.

Usage: python3 tools/check_combined.py [path-or-url-of-combined-page]
Needs Playwright for Python and a Chromium (uses /opt/pw-browsers/chromium if it exists).
"""
import asyncio
import os
import pathlib
import sys

from playwright.async_api import async_playwright

ROOT = pathlib.Path(__file__).resolve().parents[1]
TARGET = sys.argv[1] if len(sys.argv) > 1 else str(ROOT / 'hydraulics.html')
URL = TARGET if '://' in TARGET else pathlib.Path(TARGET).resolve().as_uri()
STANDALONE = {'servo': 'hydraulic_control.html', 'ideal': 'hydraulic.html', 'theory': 'hydraulic_theory.html'}
CHROMIUM = '/opt/pw-browsers/chromium'

INVENTORY = """() => {
  const q = s => document.querySelectorAll(s).length;
  return { h1: q('h1'), h2: q('h2'), h3: q('h3'), h4: q('h4'), canvas: q('canvas'), figure: q('figure'),
           katex: q('.katex'), range: q('input[type=range]'), button: q('button'), select: q('select'),
           links: q('a[href]'), table: q('table'), details: q('details'), img: q('img'),
           text: document.body.innerText.length };
}"""
PAINTED = """id => { const c = document.getElementById(id); if (!c || !c.width) return 0;
  const d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data; let n = 0;
  for (let i = 3; i < d.length; i += 4 * 61) if (d[i]) n++; return n; }"""

results = []


def check(name, ok, detail=''):
    results.append(ok)
    print(f"{'ok  ' if ok else 'FAIL'}  {name}{('  (' + detail + ')') if detail else ''}")


async def wait_status(frame, timeout=30):
    for _ in range(timeout * 10):
        s = await frame.evaluate("() => (document.getElementById('status') || {}).textContent || ''")
        if 'complete' in s.lower() or 'error' in s.lower():
            return s
        await asyncio.sleep(0.1)
    return ''


async def frame_for(page, tab):
    for _ in range(200):
        for f in page.frames:
            if f is page.main_frame:
                continue
            try:
                title = await f.evaluate('() => document.title')
            except Exception:
                continue
            want = {'servo': 'Servo-Hydraulic', 'ideal': 'Ideal Hydraulic', 'theory': 'Hydraulics from First'}[tab]
            if want in title and await f.evaluate("() => document.readyState") == 'complete':
                return f
        await asyncio.sleep(0.1)
    raise RuntimeError(f'no frame for {tab}')


async def selected(page):
    return await page.evaluate("() => document.querySelector('nav [aria-selected=true]').id.slice(4)")


async def main():
    async with async_playwright() as p:
        kw = {'executable_path': CHROMIUM} if os.path.exists(CHROMIUM) else {}
        browser = await p.chromium.launch(**kw)
        # A site without /favicon.ico answers the browser's automatic request with 404; that is not the page's error.
        _new_page = browser.new_page

        async def new_page(**k):
            pg = await _new_page(**k)
            await pg.route('**/favicon.ico', lambda route: route.fulfill(status=204))
            return pg
        browser.new_page = new_page

        # ---- reference: the standalone pages
        ref = {}
        for tab, file in STANDALONE.items():
            pg = await browser.new_page(viewport={'width': 1440, 'height': 1000})
            await pg.goto((ROOT / file).as_uri())
            if tab == 'servo':
                await wait_status(pg.main_frame)
            ref[tab] = await pg.evaluate(INVENTORY)
            await pg.close()

        # ---- the combined page
        page = await browser.new_page(viewport={'width': 1440, 'height': 1000})
        errors = []
        page.on('pageerror', lambda e: errors.append(f'pageerror: {e}'))
        page.on('console', lambda m: errors.append(f'console: {m.text}') if m.type == 'error' else None)
        await page.goto(URL)
        check('opens on the servo press tab', await selected(page) == 'servo')

        frames = {}
        for tab in ('servo', 'ideal', 'theory'):
            await page.click(f'#tab-{tab}')
            frames[tab] = f = await frame_for(page, tab)
            check(f'{tab}: tab selected after click', await selected(page) == tab)
            if tab == 'servo':
                status = await wait_status(f)
                check('servo: cycle computed in the background', 'complete' in status.lower(), status[:90])
                check('servo: energy audit closes', '✓' in status)
            got = await f.evaluate(INVENTORY)
            same = {k: (got[k], ref[tab][k]) for k in got if k != 'text' and got[k] != ref[tab][k]}
            check(f'{tab}: same elements as the standalone page', not same, str(same) if same else
                  f"{got['h2']} h2, {got['canvas']} canvases, {got['figure']} figures, {got['katex']} formulas, "
                  f"{got['range']} sliders, {got['links']} links")
            check(f'{tab}: same amount of text', abs(got['text'] - ref[tab]['text']) <= 2,
                  f"{got['text']} vs {ref[tab]['text']} characters")

        # ---- servo press works
        servo = frames['servo']
        await page.click('#tab-servo')
        check('servo: drawing painted', await servo.evaluate(PAINTED, 'scene') > 100)
        for cid in ('pl_y', 'pl_F', 'bode', 'nyq', 'zpl'):
            check(f'servo: plot {cid} drawn', await servo.evaluate(PAINTED, cid) > 20)
        t0 = float(await servo.evaluate("() => document.getElementById('scrub').value"))
        await servo.click('#play')
        await asyncio.sleep(1.5)
        t1 = float(await servo.evaluate("() => document.getElementById('scrub').value"))
        check('servo: Play advances the animation', t1 > t0, f'{t0:.3f} -> {t1:.3f}')
        await servo.click('#play')
        before = await servo.evaluate("() => document.getElementById('status').textContent")
        await servo.evaluate("""() => { const s = document.getElementById('in_Fref');
            s.value = 40; s.dispatchEvent(new Event('input', {bubbles: true})); s.dispatchEvent(new Event('change', {bubbles: true})); }""")
        after = before
        for _ in range(200):
            await asyncio.sleep(0.1)
            after = await servo.evaluate("() => document.getElementById('status').textContent")
            if after != before and 'complete' in after.lower():
                break
        check('servo: moving the force slider recomputes the cycle', after != before and 'target of 40' in after,
              after[:80])

        # ---- ideal press works
        await page.click('#tab-ideal')
        ideal = frames['ideal']
        check('ideal: drawing painted', await ideal.evaluate(PAINTED, 'scene') > 100)
        t0 = float(await ideal.evaluate("() => document.getElementById('scrub').value"))
        await ideal.click('#play')
        await asyncio.sleep(1.5)
        t1 = float(await ideal.evaluate("() => document.getElementById('scrub').value"))
        check('ideal: Play advances the animation', t1 > t0, f'{t0:.3f} -> {t1:.3f}')
        await ideal.click('#play')
        link = ideal.locator('a[href="hydraulic_theory.html"]').first
        await link.click()
        await asyncio.sleep(0.3)
        check('ideal: link to the theory switches to the Theory tab', await selected(page) == 'theory')

        # ---- theory works
        theory = frames['theory']
        y0 = await theory.evaluate('() => scrollY')
        await theory.locator('nav.toc a[href="#control"], nav.toc a').nth(12).click()
        await asyncio.sleep(1.2)
        y1 = await theory.evaluate('() => scrollY')
        check('theory: a contents link scrolls the page', y1 > y0 + 500, f'scrollY {y0} -> {y1}')
        await theory.evaluate("() => document.querySelector('a[href=\"hydraulic_control.html\"]').scrollIntoView()")
        await theory.locator('a[href="hydraulic_control.html"]').first.click()
        await asyncio.sleep(0.3)
        check('theory: link to the servo press switches to the Servo tab', await selected(page) == 'servo')

        check('no script errors in the page or its tabs', not errors, '; '.join(errors[:3]))
        await page.close()

        # ---- deep links
        for tab in ('ideal', 'theory', 'servo'):
            pg = await browser.new_page(viewport={'width': 1024, 'height': 800})
            await pg.goto(URL + '#' + tab)
            await frame_for(pg, tab)
            check(f'#{tab} opens the {tab} tab', await selected(pg) == tab)
            await pg.close()

        # ---- layout
        for w in (360, 390, 1024, 1440):
            pg = await browser.new_page(viewport={'width': w, 'height': 800})
            await pg.goto(URL)
            bad = []
            for tab in ('servo', 'ideal', 'theory'):
                await pg.click(f'#tab-{tab}')
                f = await frame_for(pg, tab)
                await asyncio.sleep(0.4)
                sw = await f.evaluate('() => [document.documentElement.scrollWidth, document.documentElement.clientWidth]')
                if sw[0] > sw[1] + 1:
                    bad.append(f'{tab} {sw[0]}>{sw[1]}')
            sw = await pg.evaluate('() => [document.documentElement.scrollWidth, innerWidth]')
            if sw[0] > sw[1] + 1:
                bad.append(f'shell {sw[0]}>{sw[1]}')
            check(f'{w} px: nothing scrolls sideways', not bad, ', '.join(bad))
            await pg.close()

        await browser.close()
    print(f"\n{'ALL ' + str(len(results)) + ' BROWSER CHECKS PASSED' if all(results) else str(results.count(False)) + ' OF ' + str(len(results)) + ' BROWSER CHECKS FAILED'}")
    sys.exit(0 if all(results) else 1)


asyncio.run(main())
