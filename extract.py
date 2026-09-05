#!/usr/bin/env python3
"""extract.py — leest een bestaande website uit en schrijft klanten/<map>/content.json.

    python3 extract.py https://doelsite.nl klanten/doelsite [--branche hoveniers] [--max-paginas 8]

Haalt op: bedrijfsnaam, adres, telefoon, e-mail, KvK, social links, logo, diensten (uit
menu en koppen), projecten (foto + titel), alle kandidaat-foto's met bron-URL, en de
intro-tekst van de huidige site. Verzint niets; wat ontbreekt blijft leeg en komt in
NALOPEN.md.
"""
import argparse, html, json, os, re, sys, urllib.parse
from sitescan import haal, decodeer, host_van, kaal

PAGINA_WOORDEN = ["dienst", "service", "over", "wie", "project", "portfolio", "referent", "werk", "foto", "galer",
                  "contact", "aanbod", "wat-we-doen", "specialis", "tuin", "team"]
SOCIALS = {"facebook": r"facebook\.com/[^\"'\s?]+", "instagram": r"instagram\.com/[^\"'\s?]+",
           "linkedin": r"linkedin\.com/(?:company|in)/[^\"'\s?]+", "youtube": r"youtube\.com/[^\"'\s?]+",
           "tiktok": r"tiktok\.com/@[^\"'\s?]+"}
NAV_SKIP = {"home", "start", "welkom", "contact", "login", "inloggen", "privacy", "disclaimer", "sitemap", "nieuws",
            "blog", "vacatures", "algemene voorwaarden", "cookies", "menu", "zoeken", "english", "en", "de", "fr",
            "werkzaamheden", "diensten", "services", "portfolio", "projecten", "referenties", "over ons", "team", "wie zijn wij",
            "foto's", "fotos", "galerij", "offerte", "offerte aanvragen", "prijzen", "tarieven", "links", "partners", "downloads"}


def schoon(t):
    t = html.unescape(re.sub(r"<[^>]+>", " ", t))
    return re.sub(r"\s+", " ", t).strip()


def tekst_van(h):
    h = re.sub(r"<(script|style|noscript|svg)[^>]*>.*?</\1>", " ", h, flags=re.S | re.I)
    return schoon(h)


def titel_uit(h):
    m = re.search(r"<title[^>]*>(.*?)</title>", h, re.I | re.S)
    return schoon(m.group(1)) if m else ""


def bedrijfsnaam(h, host, hint=None):
    kandidaten = []
    m = re.search(r'property=["\']og:site_name["\'][^>]+content=["\']([^"\']+)', h, re.I)
    if m:
        kandidaten.append(schoon(m.group(1)))
    m = re.search(r'"@type"\s*:\s*"(?:LocalBusiness|Organization|[A-Za-z]+Business|Store|HomeAndConstructionBusiness)"[^}]*?"name"\s*:\s*"([^"]+)"', h)
    if m:
        kandidaten.append(schoon(m.group(1)))
    t = titel_uit(h)
    if t:
        # "Diensten | Bedrijf X" of "Bedrijf X - Hovenier in Y"
        delen = re.split(r"\s+[|\-–—·»:]\s+", t)
        delen = [d for d in delen if d and not re.search(r"^(home|welkom|start)$", d, re.I)]
        if delen:
            kandidaten.append(max(delen, key=len) if len(delen) == 1 else min(delen, key=len))
    m = re.search(r'<img[^>]+alt=["\']([^"\']*logo[^"\']*)["\']', h, re.I)
    if m:
        kandidaten.append(re.sub(r"\blogo\b|van", "", schoon(m.group(1)), flags=re.I).strip(" -|"))
    m = re.search(r"<h1[^>]*>(.*?)</h1>", h, re.I | re.S)
    if m and 2 < len(schoon(m.group(1))) < 40 and not re.search(r"welkom|home", schoon(m.group(1)), re.I):
        kandidaten.append(schoon(m.group(1)))
    kandidaten = [k for k in kandidaten if 2 < len(k) < 60 and not re.search(r"^(home|welkom|start|homepage)$", k, re.I)]
    if hint and 2 < len(hint) < 60:
        kandidaten.append(hint)
    if not kandidaten:
        naam = kaal(host).split(".")[0]
        return naam.replace("-", " ").title()
    return kandidaten[0]


STRAAT_SUFFIX = r"(straat|weg|laan|plein|dijk|kade|singel|pad|hof|steeg|dreef|baan|markt|gracht|park|ring|erf|allee|vaart|wal|plantsoen|akker|kamp|veld|land|hoek|zijde|boulevard|route)$"


def adres_uit(tekst, naam=""):
    # Nederlands adres: Straatnaam 12a, 1234 AB Plaats
    m = re.search(r"([A-Z][\w'.\- ]{2,40}?\s\d{1,4}\s?[a-zA-Z]?(?:-\d+)?)[,\s|·]+(\d{4}\s?[A-Z]{2})\s+([A-Z][\w'\- ]{1,30}?)(?=[\s,.|·<]|$)", tekst)
    if m:
        straat = m.group(1).strip()
        woorden = straat.split()
        nummer = woorden[-1] if not re.search(r"\d", woorden[-2]) else " ".join(woorden[-2:])
        rest = woorden[:-1] if nummer == woorden[-1] else woorden[:-2]
        naamwoorden = {w.lower() for w in re.findall(r"\w+", naam)}
        # laatste 'straatachtige' woord (dichtst bij het huisnummer) is de straat; woorden
        # uit de bedrijfsnaam ervoor horen er niet bij
        idx = None
        for i in range(len(rest) - 1, -1, -1):
            if re.search(STRAAT_SUFFIX, rest[i].lower()):
                idx = i
                if i > 0 and rest[i - 1].lower() in ("oude", "nieuwe", "korte", "lange", "van", "de", "het", "hoge", "lage", "grote", "kleine", "noord", "zuid", "oost", "west", "burgemeester", "burg.", "prof.", "dr.", "mr.", "prins", "koningin", "sint", "st.", "graaf", "jan", "willem"):
                    idx = i - 1
                break
        if idx is None:
            idx = 0
            while idx < len(rest) - 1 and rest[idx].lower() in naamwoorden:
                idx += 1
            idx = max(idx, len(rest) - 3)
        straat = " ".join(rest[idx:] + [nummer])
        return {"straat": straat, "postcode": re.sub(r"\s", " ", m.group(2)), "plaats": m.group(3).strip()}
    m = re.search(r"(\d{4}\s?[A-Z]{2})\s+([A-Z][\w'\- ]{1,30}?)(?=[\s,.|·<]|$)", tekst)
    if m:
        return {"straat": None, "postcode": m.group(1), "plaats": m.group(2).strip()}
    return {}


def interne_links(h, basis):
    host = host_van(basis)
    links = []
    for m in re.finditer(r'<a\b[^>]*href=["\']([^"\'#]+)["\'][^>]*>(.*?)</a>', h, re.I | re.S):
        u = urllib.parse.urljoin(basis, m.group(1).strip())
        if host_van(u) != host:
            continue
        if re.search(r"\.(pdf|jpe?g|png|gif|zip|docx?)(\?|$)|mailto:|tel:|javascript:", u, re.I):
            continue
        u = u.split("#")[0]
        tekst = schoon(m.group(2))[:60]
        links.append((u, tekst))
    return links


def nav_items(h, basis):
    # menu-teksten: uit <nav> of de eerste <ul> met veel links
    delen = re.findall(r"<nav\b.*?</nav>", h, re.I | re.S) or re.findall(r"<ul\b[^>]*(?:menu|nav)[^>]*>.*?</ul>", h, re.I | re.S)
    items = []
    for d in delen[:3]:
        for u, t in interne_links(d, basis):
            if t and t.lower() not in NAV_SKIP and len(t) < 40:
                items.append((u, t))
    gezien = set(); uniek = []
    for u, t in items:
        if t.lower() not in gezien:
            gezien.add(t.lower()); uniek.append((u, t))
    return uniek


def koppen(h):
    return [schoon(k) for k in re.findall(r"<h[23][^>]*>(.*?)</h[23]>", h, re.I | re.S) if schoon(k)]


def beelden_uit(h, basis):
    uit = []
    for tag in re.findall(r"<img\b[^>]*>", h, re.I):
        src = None
        for attr in ("data-src", "data-lazy-src", "data-original", "src"):
            m = re.search(r'\s' + attr + r'=["\']([^"\']+)', tag, re.I)
            if m and not m.group(1).startswith("data:"):
                src = m.group(1); break
        ms = re.search(r'\ssrcset=["\']([^"\']+)', tag, re.I)
        if ms:
            # grootste variant uit srcset
            kand = []
            for deel in ms.group(1).split(","):
                p = deel.strip().split()
                if p:
                    w = int(re.sub(r"\D", "", p[1])) if len(p) > 1 and re.sub(r"\D", "", p[1]) else 0
                    kand.append((w, p[0]))
            if kand:
                src = max(kand)[1]
        if not src:
            continue
        u = urllib.parse.urljoin(basis, src)
        if u.startswith("http"):
            alt = re.search(r'\salt=["\']([^"\']*)', tag, re.I)
            klasse = re.search(r'\sclass=["\']([^"\']*)', tag, re.I)
            w = re.search(r'\swidth=["\']?(\d+)', tag, re.I); hh = re.search(r'\sheight=["\']?(\d+)', tag, re.I)
            uit.append({"url": u, "alt": schoon(alt.group(1)) if alt else "", "class": klasse.group(1) if klasse else "",
                        "w": int(w.group(1)) if w else None, "h": int(hh.group(1)) if hh else None})
    # achtergrondbeelden in inline style
    for m in re.finditer(r"background(?:-image)?\s*:\s*url\(([^)]+)\)", h, re.I):
        u = urllib.parse.urljoin(basis, m.group(1).strip("'\" "))
        if u.startswith("http") and re.search(r"\.(jpe?g|png|webp)", u, re.I):
            uit.append({"url": u, "alt": "", "class": "achtergrond", "w": None, "h": None})
    return uit


def timthumb_bron(u):
    m = re.search(r"timthumb\.php\?.*?src=([^&]+)", u)
    if m:
        return urllib.parse.unquote(m.group(1))
    return u


def logo_kandidaat(beelden, h):
    for b in beelden:
        s = (b["url"] + " " + b["alt"] + " " + b["class"]).lower()
        if "logo" in s and not re.search(r"footer|partner|keurmerk|payment|ideal", s):
            return b["url"]
    m = re.search(r'<header\b.*?<img[^>]+src=["\']([^"\']+)', h, re.I | re.S)
    if m:
        return m.group(1)
    m = re.search(r'rel=["\']apple-touch-icon[^"\']*["\'][^>]+href=["\']([^"\']+)', h, re.I)
    return m.group(1) if m else None


def intro_tekst(h):
    """Eerste inhoudelijke alinea van de homepage (overgenomen tekst, geen verzinsel)."""
    body = re.split(r"<main\b|<body\b", h, flags=re.I)[-1]
    body = re.sub(r"<(script|style|nav|header|footer|noscript)[^>]*>.*?</\1>", " ", body, flags=re.S | re.I)
    alineas = [schoon(p) for p in re.findall(r"<p\b[^>]*>(.*?)</p>", body, re.I | re.S)]
    alineas += [schoon(p) for p in re.findall(r"<div\b[^>]*>([^<]{80,600})</div>", body, re.I | re.S)]
    alineas = [a for a in alineas if 80 <= len(a) <= 600 and not re.search(r"cookie|privacy|©|copyright|inloggen|javascript|niet bereikbaar|gesloten|vakantie|i\.?v\.?m\.?|wegens|tijdelijk|\b\d{1,2} (januari|februari|maart|april|mei|juni|juli|augustus|september|oktober|november|december)\b", a, re.I)]
    if alineas:
        return alineas[0]
    m = re.search(r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']{40,})', h, re.I)
    return schoon(m.group(1)) if m else None


def extract(url, map_uit, branche=None, max_paginas=8, log=print, naam_hint=None):
    os.makedirs(map_uit, exist_ok=True)
    if not re.match(r"^https?://", url, re.I):
        url = "http://" + url
    st, eind, body, hdr, sec = haal(url, timeout=20)
    if not body:
        raise RuntimeError(f"geen inhoud van {url} (status {st})")
    h = decodeer(body, hdr)
    basis = eind
    host = host_van(basis)
    paginas = {basis: h}
    # pagina's kiezen: menu-items eerst, dan links met relevante woorden
    kandidaten = [u for u, t in nav_items(h, basis)]
    for u, t in interne_links(h, basis):
        if any(w in (u + " " + t).lower() for w in PAGINA_WOORDEN):
            kandidaten.append(u)
    gezien = {basis.rstrip("/"), basis.rstrip("/") + "/index.html", basis.rstrip("/") + "/index.php"}
    for u in kandidaten:
        if len(paginas) >= max_paginas:
            break
        if u.rstrip("/") in gezien:
            continue
        gezien.add(u.rstrip("/"))
        try:
            st2, e2, b2, h2, s2 = haal(u, timeout=15)
            if st2 < 400 and b2 and b"<html" in b2[:5000].lower():
                paginas[u] = decodeer(b2, h2)
                log(f"  gelezen: {u}")
        except Exception as e:
            log(f"  overgeslagen: {u} ({e.__class__.__name__})")
    alle_tekst = " ".join(tekst_van(p) for p in paginas.values())
    alle_html = "\n".join(paginas.values())

    naam = bedrijfsnaam(h, host, naam_hint)
    adres = adres_uit(tekst_van(h), naam) or adres_uit(alle_tekst, naam)
    mails = sorted({m.lower().rstrip(".") for m in re.findall(r"[\w.+-]+@[\w-]+\.[\w.-]+", html.unescape(alle_html))
                    if not re.search(r"\.(png|jpe?g|gif|svg|webp|css|js)$", m, re.I) and "example" not in m and "wixpress" not in m and "sentry" not in m}
                   | {m.lower() for m in re.findall(r'mailto:([^"\'?]+)', alle_html, re.I)},
                  key=lambda m: (0 if m.startswith("info@") else 1, 0 if kaal(host) in m else 1, m))
    tels = []
    for t in re.findall(r"(?:\+31|0031|0)[\s\-]?(?:\(0\))?[\s\-]?(?:\d[\s\-]?){8,9}\d", alle_tekst):
        c = re.sub(r"\D", "", t)
        if c.startswith("31"):
            c = "0" + c[2:]
        if len(c) == 10 and c.startswith("0") and c not in tels:
            tels.append(c)
    mk = re.search(r"(?:kvk|k\.v\.k\.|kamer van koophandel)[^\d]{0,25}(\d{8})", alle_tekst, re.I)
    socials = {}
    for k, pat in SOCIALS.items():
        m = re.search(r"https?://(?:www\.)?" + pat, alle_html, re.I)
        if m:
            socials[k] = m.group(0).rstrip("/")
    # diensten: menu-items onder een 'diensten'-pagina, anders koppen op die pagina, anders menu
    diensten = []
    for u, p in paginas.items():
        if re.search(r"dienst|service|aanbod|specialis|wat-we-doen", u, re.I) and u != basis:
            for k in koppen(p):
                if 3 < len(k) < 45 and k.lower() not in NAV_SKIP and not re.search(r"contact|offerte|meer weten|neem|bel ", k, re.I):
                    diensten.append(k)
    if len(diensten) < 3:
        for u, t in nav_items(h, basis):
            if t.lower() not in NAV_SKIP and not re.search(r"over|project|referent|foto|galer|nieuws|contact|home", t, re.I):
                diensten.append(t)
    gezien = set(); diensten = [d for d in diensten if not (d.lower() in gezien or gezien.add(d.lower()))][:8]
    # beelden en projecten
    beelden = []
    gezien_b = set()
    for u, p in paginas.items():
        for b in beelden_uit(p, u):
            b["url"] = timthumb_bron(b["url"])
            b["url"] = re.sub(r"_s\.jpg$", "_b.jpg", b["url"])   # flickr thumbnails
            sleutel = re.sub(r"-\d{2,4}x\d{2,4}(?=\.\w+$)", "", b["url"])
            if sleutel in gezien_b:
                continue
            gezien_b.add(sleutel)
            b["pagina"] = u
            beelden.append(b)
    projecten = []
    for u, p in paginas.items():
        if re.search(r"project|portfolio|referent|werk|foto|galer|tuin", u, re.I) and u != basis:
            for m in re.finditer(r"<(?:figure|article|div)\b[^>]*>(.*?)</(?:figure|article|div)>", p, re.I | re.S):
                blok = m.group(1)
                img = re.search(r'<img[^>]+(?:data-src|src)=["\']([^"\']+)', blok, re.I)
                if not img:
                    continue
                titel = None
                for pat in (r"<(?:h[2-4]|figcaption)[^>]*>(.*?)</(?:h[2-4]|figcaption)>", r'\salt=["\']([^"\']{4,80})["\']', r"<(?:strong|b)>(.*?)</(?:strong|b)>"):
                    mt = re.search(pat, blok, re.I | re.S)
                    if mt and 3 < len(schoon(mt.group(1))) < 80:
                        titel = schoon(mt.group(1)); break
                if not titel:
                    continue
                src = timthumb_bron(urllib.parse.urljoin(u, img.group(1)))
                src = re.sub(r"_s\.jpg$", "_b.jpg", src)
                sleutel = re.sub(r"-\d{2,4}x\d{2,4}(?=\.\w+$)", "", src).lower()
                if re.search(r"logo|icon|socialmedia|lees meer|bekijk|^(foto|impressie|galerij|album|overzicht|contact|projecten?)\b", titel + " " + src, re.I):
                    continue
                if re.search(r"^(img|dsc|p\d|dscn|_mg|photo|image|afbeelding|foto)[\s_\-]?\d", titel, re.I) or re.fullmatch(r"[\w\-]+\d[\w\-]*", titel):
                    continue   # bestandsnaam als titel
                if titel.lower() == naam.lower():
                    continue
                if any(pr["titel"].lower() == titel.lower() or pr["sleutel"] == sleutel for pr in projecten):
                    continue
                projecten.append({"titel": titel, "foto": src, "bron": u, "sleutel": sleutel})
    projecten = [{k: v for k, v in p.items() if k != "sleutel"} for p in projecten[:9]]
    content = {
        "bron_url": basis, "domein": kaal(host), "branche": branche,
        "naam": naam, "adres": adres, "telefoon": tels[:2], "email": mails[0] if mails else None, "emails": mails[:4],
        "kvk": mk.group(1) if mk else None, "socials": socials,
        "logo": urllib.parse.urljoin(basis, logo_kandidaat(beelden, h)) if logo_kandidaat(beelden, h) else None,
        "diensten": diensten, "projecten": projecten, "intro": intro_tekst(h),
        "titel_huidig": titel_uit(h), "paginas_gelezen": list(paginas.keys()),
        "beelden": beelden[:80],
        "theme_color": (re.search(r'name=["\']theme-color["\'][^>]+content=["\'](#[0-9a-fA-F]{3,6})', h) or [None, None])[1],
    }
    json.dump(content, open(os.path.join(map_uit, "content.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    log(f"content.json: {naam} · {len(paginas)} pagina's · {len(beelden)} beelden · {len(projecten)} projecten · {len(diensten)} diensten")
    return content


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("url"); ap.add_argument("map")
    ap.add_argument("--branche"); ap.add_argument("--max-paginas", type=int, default=8)
    a = ap.parse_args()
    extract(a.url, a.map, a.branche, a.max_paginas, log=lambda s: print(s, file=sys.stderr))


if __name__ == "__main__":
    main()
