"""Export poster.html to a 48 x 36 in PDF and PNG previews, and run layout checks.

Run from the repo root:  python poster/export.py
"""
from pathlib import Path
import json
from playwright.sync_api import sync_playwright

POSTER = Path(__file__).resolve().parent
URL = (POSTER / "poster.html").as_uri()
W, H, M = 4608, 3456, 72

CHECK_JS = """
([W, H, M]) => {
  const out = [];
  for (const el of document.querySelectorAll('.page *')) {
    const r = el.getBoundingClientRect();
    if (!r.width || !r.height) continue;
    if (r.left < M - 0.5 || r.top < M - 0.5 || r.right > W - M + 0.5 || r.bottom > H - M + 0.5)
      out.push({type: 'outside-margin', el: el.tagName + '.' + el.className, r: [r.left, r.top, r.right, r.bottom].map(Math.round)});
    if (el.scrollWidth > el.clientWidth + 1 && getComputedStyle(el).overflow !== 'visible')
      out.push({type: 'clipped-x', el: el.tagName + '.' + el.className});
  }
  const cols = [...document.querySelectorAll('.col')].map(c => {
    const last = c.lastElementChild.getBoundingClientRect();
    const kids = [...c.children].reduce((s, k) => s + k.getBoundingClientRect().height, 0);
    return {bottom: Math.round(c.getBoundingClientRect().bottom), contentBottom: Math.round(last.bottom),
            scroll: c.scrollHeight, client: c.clientHeight,
            free: Math.round(c.clientHeight - kids - (c.children.length - 1) * parseFloat(getComputedStyle(c).rowGap))};
  });
  // smallest rendered font size, ignoring the references block
  let minFont = 999, minEl = '';
  for (const el of document.querySelectorAll('.page *')) {
    if (el.closest('.refs')) continue;
    const t = [...el.childNodes].some(n => n.nodeType === 3 && n.textContent.trim());
    if (!t) continue;
    const f = parseFloat(getComputedStyle(el).fontSize);
    if (f < minFont) { minFont = f; minEl = el.tagName + '.' + el.className + ': ' + el.textContent.trim().slice(0, 40); }
  }
  const imgs = [...document.querySelectorAll('img')].map(i => {
    const r = i.getBoundingClientRect();
    return {src: i.getAttribute('src'), natural: [i.naturalWidth, i.naturalHeight],
            shown_in: [+(r.width / 96).toFixed(2), +(r.height / 96).toFixed(2)],
            dpi: Math.round(i.naturalWidth / (r.width / 96))};
  });
  const words = document.querySelector('.page').innerText.split(/\\s+/).filter(Boolean).length;
  return {problems: out.slice(0, 40), nProblems: out.length, cols, minFontPx: minFont, minFontPt: minFont * 0.75, minEl, imgs, words};
}
"""

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": W, "height": H}, device_scale_factor=1)
    page.goto(URL, wait_until="networkidle")
    page.evaluate("document.fonts.ready")
    report = page.evaluate(CHECK_JS, [W, H, M])
    print(json.dumps(report, indent=1))
    page.pdf(path=str(POSTER / "poster.pdf"), width="48in", height="36in",
             print_background=True, prefer_css_page_size=True)
    for scale, name in [(0.10, "preview_10pct.png"), (0.25, "preview_25pct.png")]:
        pg = browser.new_page(viewport={"width": W, "height": H}, device_scale_factor=scale)
        pg.goto(URL, wait_until="networkidle")
        pg.evaluate("document.fonts.ready")
        pg.screenshot(path=str(POSTER / name), full_page=False)
        pg.close()
    browser.close()
print("exported")
