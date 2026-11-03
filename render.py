import os
import re
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright

OUT_DIR = "simplisafe"
TITLE_WAIT_MS = 25000
SETTLE_MS = 2500
os.makedirs(OUT_DIR, exist_ok=True)

SLIM_JS = """() => {
  const c = document.documentElement.cloneNode(true);
  c.querySelectorAll('script:not([type="application/ld+json"]), style, svg, noscript, template')
   .forEach(e => e.remove());
  c.querySelectorAll('link').forEach(l => {
    const rel = (l.getAttribute('rel') || '').toLowerCase();
    if (!rel.includes('canonical') && !(rel.includes('alternate') && l.getAttribute('hreflang'))) l.remove();
  });
  c.querySelectorAll('[srcset], [sizes]').forEach(e => { e.removeAttribute('srcset'); e.removeAttribute('sizes'); });
  c.querySelectorAll('picture source').forEach(e => e.remove());
  c.querySelectorAll('*').forEach(el => {
    [...el.attributes].forEach(a => {
      if (a.name.startsWith('data-') && a.name !== 'data-bg' && a.value.length > 800) el.removeAttribute(a.name);
    });
  });
  return '<!DOCTYPE html>' + c.outerHTML;
}"""

def slug(url):
    u = urlparse(url)
    s = re.sub(r"[^a-zA-Z0-9]+", "_", (u.netloc + u.path).strip("/")).strip("_")
    return s[:120] or "page"

urls = [l.strip() for l in open("urls.txt") if l.strip() and not l.startswith("#")]

with sync_playwright() as p:
    browser = p.chromium.launch(args=["--no-sandbox"])
    ctx = browser.new_context(
        viewport={"width": 1366, "height": 900}, locale="en-US",
        user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"))
    for url in urls:
        page = ctx.new_page()
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            try:
                page.wait_for_function("document.title && document.title.trim() !== ''",
                                       timeout=TITLE_WAIT_MS)
            except Exception:
                print("WARN title did not appear:", url)
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(SETTLE_MS)
            html = page.evaluate(SLIM_JS)
            if not (page.title() or "").strip():
                print("SKIP no title, keeping previous copy:", url)
                continue
            with open(os.path.join(OUT_DIR, slug(url) + ".html"), "w", encoding="utf-8") as f:
                f.write(html)
            print("OK", url, len(html))
        except Exception as e:
            print("ERROR", url, type(e).__name__, str(e)[:200])
        finally:
            page.close()
    browser.close()
