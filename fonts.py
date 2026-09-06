#!/usr/bin/env python3
"""fonts.py — haalt de lettertypes (OFL-licentie, via Google Fonts) één keer op naar vendor/fonts/,
zodat elke demo ze zelf meelevert en niets van Google laadt (AVG-nette oplossing).

    python3 fonts.py            # vult vendor/fonts/ (alleen latin-subset, woff2)

Per familie: <sleutel>.woff2 (variabel lettertype) + <sleutel>.css met de @font-face-regels
(zonder unicode-range, één bestand per familie). build.py kopieert wat een stijl nodig heeft
naar web/fonts/ en plakt de @font-face-regels in de pagina-CSS.
"""
import os, re, sys, ssl, urllib.request

HIER = os.path.dirname(os.path.abspath(__file__))
MAP = os.path.join(HIER, "vendor", "fonts")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
CTX = ssl.create_default_context(); CTX.check_hostname = False; CTX.verify_mode = ssl.CERT_NONE

# sleutel → (familienaam, as-specificatie voor css2)
FAMILIES = {
    "fraunces": ("Fraunces", "opsz,wght@9..144,500..700"),
    "worksans": ("Work Sans", "wght@400..600"),
    "barlowcondensed": ("Barlow Condensed", "wght@600;700"),
    "barlow": ("Barlow", "wght@400;600"),
    "nunito": ("Nunito", "wght@400..800"),
    "playfair": ("Playfair Display", "wght@500..700"),
    "sourcesans": ("Source Sans 3", "wght@400..600"),
    "manrope": ("Manrope", "wght@400..800"),
    "lora": ("Lora", "wght@400..600"),
}


def haal(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30, context=CTX) as r:
        return r.read()


def main():
    os.makedirs(MAP, exist_ok=True)
    for sleutel, (fam, assen) in FAMILIES.items():
        css = haal(f"https://fonts.googleapis.com/css2?family={fam.replace(' ', '+')}:{assen}&display=swap").decode()
        # alleen het latin-blok (staat als laatste)
        blokken = re.findall(r"/\* (\w[\w-]*) \*/\s*@font-face\s*\{(.*?)\}", css, re.S)
        latin = [b for n, b in blokken if n == "latin"]
        if not latin:
            print(f"  {sleutel}: geen latin-blok gevonden", file=sys.stderr); continue
        regels = []
        for i, blok in enumerate(latin):
            url = re.search(r"url\((https://[^)]+)\)", blok).group(1)
            gewicht = re.search(r"font-weight:\s*([^;]+);", blok).group(1).strip()
            stijl = re.search(r"font-style:\s*([^;]+);", blok).group(1).strip()
            bestand = f"{sleutel}{'' if len(latin) == 1 else '-' + str(i)}.woff2"
            data = haal(url)
            open(os.path.join(MAP, bestand), "wb").write(data)
            regels.append(f"@font-face{{font-family:'{fam}';font-style:{stijl};font-weight:{gewicht};font-display:swap;src:url(fonts/{bestand}) format('woff2')}}")
            print(f"  {bestand}: {len(data)//1024} kB ({gewicht})", file=sys.stderr)
        open(os.path.join(MAP, f"{sleutel}.css"), "w").write("\n".join(regels) + "\n")


if __name__ == "__main__":
    main()
