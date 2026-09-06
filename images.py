#!/usr/bin/env python3
"""images.py — haalt de foto's van de bestaande site op, maakt er WebP van en kiest
logo, hero-foto, projectfoto's en galerijbeelden. Schrijft klanten/<map>/images.json.

    python3 images.py klanten/<map> [--max 30] [--breedte 1400]

Regels (zie bouwstraat.md): dubbelen op '-1024x742'-suffix ontdubbelen en de grootste
houden · logo's en social-plaatjes herkennen aan beeldinhoud (kleurspreiding) · hero uit
de liggende foto's · accentkleur uit het logo, donker genoeg voor 5,2:1 op wit.
"""
import argparse, colorsys, io, json, os, re, sys, urllib.request, warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
from concurrent.futures import ThreadPoolExecutor
from PIL import Image, ImageOps, ImageStat
from sitescan import CTX, UA

Image.MAX_IMAGE_PIXELS = 60_000_000


def download(url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Referer": url.split("/", 3)[0] + "//" + url.split("/", 3)[2] + "/"})
    with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
        return r.read(25_000_000)


def sleutel(url):
    u = re.sub(r"-\d{2,4}x\d{2,4}(?=\.\w+(\?|$))", "", url.split("?")[0].lower())
    u = re.sub(r"_(thumb|small|medium|large|klein|groot)(?=\.\w+$)", "", u)
    return u


def is_foto(img):
    """Foto of grafisch element? Kleurspreiding < 24 of < 2500 unieke kleuren in 120×120 = geen foto."""
    k = img.convert("RGB").resize((120, 120))
    stat = ImageStat.Stat(k)
    spreiding = sum(stat.stddev) / 3
    uniek = len(set(k.getdata()))
    return spreiding >= 24 and uniek >= 2500


def contrast_op_wit(rgb):
    def lin(c):
        c /= 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    L = 0.2126 * lin(rgb[0]) + 0.7152 * lin(rgb[1]) + 0.0722 * lin(rgb[2])
    return 1.05 / (L + 0.05)


def accent_uit_logo(img, minimaal=5.2):
    k = img.convert("RGBA").resize((80, 80))
    tel = {}
    for r, g, b, a in k.getdata():
        if a < 128:
            continue
        h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
        if s < 0.25 or v < 0.15 or v > 0.97:
            continue  # grijs, zwart, wit overslaan
        sl = (round(h * 24), round(s * 4), round(v * 4))
        tel[sl] = tel.get(sl, 0) + 1
    if not tel:
        return None
    (hh, ss, vv), _ = max(tel.items(), key=lambda x: x[1])
    h, s, v = hh / 24, max(ss / 4, 0.45), vv / 4
    # donkerder maken tot het contrast op wit hoog genoeg is
    for _ in range(40):
        rgb = tuple(int(round(c * 255)) for c in colorsys.hsv_to_rgb(h, s, v))
        if contrast_op_wit(rgb) >= minimaal:
            break
        v -= 0.03
    return "#%02x%02x%02x" % rgb


def donkerder(hexkleur, factor=0.72):
    r, g, b = int(hexkleur[1:3], 16), int(hexkleur[3:5], 16), int(hexkleur[5:7], 16)
    return "#%02x%02x%02x" % (int(r * factor), int(g * factor), int(b * factor))


def verwerk(map_klant, maximum=30, breedte=1400, log=print):
    content = json.load(open(os.path.join(map_klant, "content.json"), encoding="utf-8"))
    uit_map = os.path.join(map_klant, "web", "img")
    os.makedirs(uit_map, exist_ok=True)
    kandidaten = []
    gezien = {}
    lijst = list(content.get("beelden", []))
    for p in content.get("projecten", []):
        lijst.append({"url": p["foto"], "alt": p["titel"], "class": "project", "w": None, "h": None})
    if content.get("logo"):
        lijst.insert(0, {"url": content["logo"], "alt": "logo", "class": "logo", "w": None, "h": None})
    for b in lijst:
        u = b["url"]
        if re.search(r"\.(svg|gif|ico)(\?|$)", u, re.I) and "logo" not in (b.get("class", "") + b.get("alt", "")).lower():
            continue
        if re.search(r"gravatar|emoji|pixel|spacer|1x1|tracking|doubleclick|facebook\.com/tr|\.php\?", u, re.I) and "timthumb" not in u:
            continue
        s = sleutel(u)
        if s in gezien:
            continue
        gezien[s] = True
        kandidaten.append(b)
    kandidaten = kandidaten[: maximum + 12]
    log(f"  {len(kandidaten)} kandidaat-beelden ophalen")

    def haal_een(b):
        try:
            data = download(b["url"])
            img = Image.open(io.BytesIO(data))
            img.load()
            return b, img, len(data)
        except Exception as e:
            return b, None, 0

    resultaten = []
    with ThreadPoolExecutor(max_workers=6) as ex:
        for b, img, grootte in ex.map(haal_een, kandidaten):
            if img is None:
                continue
            resultaten.append((b, img, grootte))
    beelden = []
    logo = None
    accent = None
    for b, img, grootte in resultaten:
        w, h = img.size
        is_logo_hint = "logo" in (b.get("class", "") + " " + b.get("alt", "") + " " + b["url"]).lower()
        foto = is_foto(img) if w >= 200 and h >= 150 else False
        if is_logo_hint and logo is None and not (foto and w > 900) and w / max(h, 1) <= 6 and h >= 24:
            # (extreem brede of piepkleine 'logo'-plaatjes zijn banners of iconen, geen logo)
            # logo: bewaren als png (transparantie) of webp
            img2 = ImageOps.exif_transpose(img)
            if img2.mode not in ("RGBA", "RGB"):
                img2 = img2.convert("RGBA")
            if img2.width > 600:
                img2 = img2.resize((600, int(img2.height * 600 / img2.width)), Image.LANCZOS)
            pad = os.path.join(uit_map, "logo.png" if "A" in img2.mode else "logo.webp")
            img2.save(pad, quality=90)
            logo = {"bestand": os.path.relpath(pad, os.path.join(map_klant, "web")).replace(os.sep, "/"), "w": img2.width, "h": img2.height, "bron": b["url"]}
            accent = accent_uit_logo(img2)
            continue
        if not foto or w < 500 or h < 300:
            continue
        img2 = ImageOps.exif_transpose(img).convert("RGB")
        if img2.width > breedte:
            img2 = img2.resize((breedte, int(img2.height * breedte / img2.width)), Image.LANCZOS)
        naam = re.sub(r"[^a-z0-9]+", "-", os.path.basename(b["url"].split("?")[0]).rsplit(".", 1)[0].lower()).strip("-")[:40] or f"beeld{len(beelden)}"
        pad = os.path.join(uit_map, f"{naam}.webp")
        i = 1
        while os.path.exists(pad):
            pad = os.path.join(uit_map, f"{naam}-{i}.webp"); i += 1
        img2.save(pad, "WEBP", quality=78, method=4)
        beelden.append({"bestand": os.path.relpath(pad, os.path.join(map_klant, "web")).replace(os.sep, "/"),
                        "w": img2.width, "h": img2.height, "bron": b["url"], "alt": b.get("alt", ""),
                        "liggend": img2.width > img2.height * 1.15, "origineel_bytes": grootte,
                        "webp_bytes": os.path.getsize(pad), "sleutel": sleutel(b["url"])})
        if len(beelden) >= maximum:
            break
    # rollen
    projecten = []
    gebruikt = set()
    for p in content.get("projecten", []):
        s = sleutel(p["foto"])
        for bb in beelden:
            if bb["sleutel"] == s and bb["bestand"] not in gebruikt:
                projecten.append({"titel": p["titel"], "beeld": bb["bestand"], "w": bb["w"], "h": bb["h"]})
                gebruikt.add(bb["bestand"]); break
    liggend = [bb for bb in beelden if bb["liggend"] and bb["bestand"] not in gebruikt]
    hero = None
    if liggend:
        hero = max(liggend, key=lambda bb: bb["w"] * bb["h"])
        gebruikt.add(hero["bestand"])
    elif beelden:
        hero = max((bb for bb in beelden if bb["bestand"] not in gebruikt), key=lambda bb: bb["w"] * bb["h"], default=None)
        if hero:
            gebruikt.add(hero["bestand"])
    # projecten aanvullen met foto's zonder titel? Nee: geen verzonnen titels. Wel galerij.
    galerij = [bb for bb in beelden if bb["bestand"] not in gebruikt][:8]
    orig = sum(bb["origineel_bytes"] for bb in beelden)
    nieuw = sum(bb["webp_bytes"] for bb in beelden)
    manifest = {"logo": logo, "accent": accent, "accent_donker": donkerder(accent) if accent else None,
                "hero": {k: hero[k] for k in ("bestand", "w", "h", "alt")} if hero else None,
                "projecten": projecten, "galerij": [{k: bb[k] for k in ("bestand", "w", "h", "alt")} for bb in galerij],
                "aantal_foto": len(beelden), "origineel_mb": round(orig / 1e6, 2), "webp_mb": round(nieuw / 1e6, 2),
                "besparing_pct": round(100 * (1 - nieuw / orig)) if orig else None}
    json.dump(manifest, open(os.path.join(map_klant, "images.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    log(f"  {len(beelden)} foto's → WebP ({manifest['origineel_mb']} MB → {manifest['webp_mb']} MB), logo {'ja' if logo else 'nee'}, accent {accent}, {len(projecten)} projecten met foto")
    return manifest


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("map"); ap.add_argument("--max", type=int, default=30); ap.add_argument("--breedte", type=int, default=1400)
    a = ap.parse_args()
    verwerk(a.map, a.max, a.breedte, log=lambda s: print(s, file=sys.stderr))


if __name__ == "__main__":
    main()
