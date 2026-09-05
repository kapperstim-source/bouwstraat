#!/usr/bin/env python3
"""verify.py — test een gebouwde demo met Playwright: kapotte links, scriptfouten,
toegankelijkheid (axe-core), horizontale scroll op mobiel, en maakt screenshots.

    python3 verify.py klanten/<map>

Schrijft klanten/<map>/verify.json en screens/*.png. Test via een lokale http-server
(niet via file://, anders geeft axe CORS-fouten die op JS-fouten lijken).
"""
import argparse, json, os, re, socket, sys, threading, urllib.parse
from functools import partial
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler

AXE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor", "axe.min.js")


class Stil(SimpleHTTPRequestHandler):
    """Zwijgt, en doet wat Cloudflare Pages doet: /diensten → diensten.html."""
    def log_message(self, *a):
        pass

    def translate_path(self, path):
        p = super().translate_path(path)
        if not os.path.exists(p) and "." not in os.path.basename(p) and os.path.exists(p + ".html"):
            return p + ".html"
        return p


def server(map_web):
    s = socket.socket(); s.bind(("127.0.0.1", 0)); poort = s.getsockname()[1]; s.close()
    httpd = ThreadingHTTPServer(("127.0.0.1", poort), partial(Stil, directory=map_web))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, f"http://127.0.0.1:{poort}"


def verifieer(map_klant, log=print):
    from playwright.sync_api import sync_playwright
    web = os.path.join(map_klant, "web")
    screens = os.path.join(map_klant, "screens")
    os.makedirs(screens, exist_ok=True)
    httpd, basis = server(web)
    paginas = [f for f in ("index.html", "diensten.html", "contact.html", "privacy.html") if os.path.exists(os.path.join(web, f))]
    uit = {"paginas": {}, "kapotte_links": [], "js_fouten": [], "axe_schendingen": [], "horizontale_scroll": [], "ok": True}
    axe_js = open(AXE, encoding="utf-8").read() if os.path.exists(AXE) else None
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for pagina in paginas:
            for naam, vp in (("desktop", {"width": 1366, "height": 900}), ("mobiel", {"width": 390, "height": 844})):
                ctx = browser.new_context(viewport=vp, device_scale_factor=1, is_mobile=(naam == "mobiel"), locale="nl-NL")
                page = ctx.new_page()
                fouten = []
                page.on("pageerror", lambda e: fouten.append(str(e)))
                page.on("console", lambda msg: fouten.append(msg.text) if msg.type == "error" else None)
                url = f"{basis}/{pagina}"
                r = page.goto(url, wait_until="load", timeout=30000)
                # lazy beelden binnenhalen: door de pagina scrollen
                page.evaluate("async () => { for (let y = 0; y < document.body.scrollHeight; y += 600) { window.scrollTo(0, y); await new Promise(r => setTimeout(r, 60)); } window.scrollTo(0, 0); }")
                page.wait_for_timeout(300)
                breed = page.evaluate("document.documentElement.scrollWidth > window.innerWidth + 1")
                if breed:
                    uit["horizontale_scroll"].append(f"{pagina} ({naam})")
                if naam == "desktop":
                    # links controleren
                    hrefs = page.evaluate("Array.from(document.querySelectorAll('a[href]')).map(a => a.getAttribute('href'))")
                    for h in set(hrefs):
                        if not h or h.startswith(("#", "mailto:", "tel:", "http", "javascript:")):
                            continue
                        doel = urllib.parse.urljoin(url, h).split("#")[0]
                        rel = urllib.parse.unquote(doel.replace(basis + "/", "").replace(basis, ""))
                        pad = os.path.join(web, rel) if rel else os.path.join(web, "index.html")
                        if os.path.isdir(pad):
                            pad = os.path.join(pad, "index.html")
                        if not os.path.exists(pad) and os.path.exists(pad + ".html"):
                            pad = pad + ".html"
                        if not os.path.exists(pad):
                            uit["kapotte_links"].append(f"{pagina} → {h}")
                    imgs = page.evaluate("Array.from(document.images).filter(i => !i.complete || i.naturalWidth === 0).map(i => i.getAttribute('src'))")
                    for s in imgs:
                        uit["kapotte_links"].append(f"{pagina} → beeld {s}")
                    if axe_js:
                        page.add_script_tag(content=axe_js)
                        res = page.evaluate("async () => { const r = await axe.run(document, {runOnly: {type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21aa']}}); return r.violations.map(v => ({id: v.id, impact: v.impact, nodes: v.nodes.length, help: v.help})); }")
                        for v in res:
                            uit["axe_schendingen"].append({"pagina": pagina, **v})
                page.screenshot(path=os.path.join(screens, f"{pagina.replace('.html', '')}-{naam}.png"), full_page=(naam == "desktop"))
                uit["paginas"][f"{pagina}/{naam}"] = {"status": r.status if r else None, "fouten": fouten}
                for f in fouten:
                    uit["js_fouten"].append(f"{pagina} ({naam}): {f[:200]}")
                ctx.close()
        browser.close()
    httpd.shutdown()
    uit["ok"] = not (uit["kapotte_links"] or uit["js_fouten"] or uit["axe_schendingen"] or uit["horizontale_scroll"])
    json.dump(uit, open(os.path.join(map_klant, "verify.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    log(f"  verify: {len(paginas)} pagina's · {len(uit['kapotte_links'])} kapotte links · {len(uit['js_fouten'])} scriptfouten · {len(uit['axe_schendingen'])} axe-schendingen · horizontale scroll: {len(uit['horizontale_scroll'])} → {'OK' if uit['ok'] else 'NIET OK'}")
    return uit


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("map")
    a = ap.parse_args()
    uit = verifieer(a.map, log=lambda s: print(s, file=sys.stderr))
    if not uit["ok"]:
        print(json.dumps({k: uit[k] for k in ("kapotte_links", "js_fouten", "axe_schendingen", "horizontale_scroll")}, ensure_ascii=False, indent=1))
        sys.exit(1)


if __name__ == "__main__":
    main()
