#!/usr/bin/env python3
"""oogst.py — bedrijven met een website ophalen uit OpenStreetMap (Overpass API).

    python3 oogst.py --branche hoveniers --regio Drenthe [--uit bedrijven.json] [--max 400]
    python3 oogst.py --branches            → lijst van bekende branches
    python3 oogst.py --regios              → lijst van bekende regio's

Wat het doet (zie prospect-pipeline.md): tegels van hooguit ±0,75°, twee spiegels met
retries (overpass-api.de reset vaak; overpass.osm.ch bevat alleen Zwitserland), filter op
.nl-domein, ketenfilialen eruit (meer dan twee vestigingen op één domein = keten).
"""
import argparse, json, re, ssl, sys, time, urllib.request, urllib.parse
from collections import Counter

SPIEGELS = ["https://overpass.private.coffee/api/interpreter",
            "https://overpass.kumi.systems/api/interpreter",
            "https://overpass-api.de/api/interpreter"]
CTX = ssl.create_default_context(); CTX.check_hostname = False; CTX.verify_mode = ssl.CERT_NONE

# OSM-tags per branche. Meerdere selectors = allemaal opgehaald.
BRANCHES = {
    "hoveniers":        [("craft", "gardener")],
    "tuincentra":       [("shop", "garden_centre")],
    "dakdekkers":       [("craft", "roofer")],
    "timmerbedrijven":  [("craft", "carpenter"), ("craft", "joiner")],
    "schilders":        [("craft", "painter")],
    "installateurs":    [("craft", "plumber"), ("craft", "hvac"), ("craft", "electrician")],
    "stukadoors":       [("craft", "plasterer")],
    "tegelzetters":     [("craft", "tiler")],
    "metselaars":       [("craft", "bricklayer")],
    "aannemers":        [("craft", "builder"), ("office", "construction_company")],
    "kappers":          [("shop", "hairdresser")],
    "schoonheidssalons": [("shop", "beauty")],
    "fysiotherapeuten": [("healthcare", "physiotherapist"), ("amenity", "physiotherapist")],
    "tandartsen":       [("amenity", "dentist")],
    "dierenartsen":     [("amenity", "veterinary")],
    "autogarages":      [("shop", "car_repair")],
    "fietsenmakers":    [("shop", "bicycle")],
    "bakkers":          [("shop", "bakery")],
    "slagers":          [("shop", "butcher")],
    "bloemisten":       [("shop", "florist")],
    "rijscholen":       [("amenity", "driving_school")],
    "makelaars":        [("office", "estate_agent")],
    "restaurants":      [("amenity", "restaurant")],
    "cafes":            [("amenity", "cafe")],
    "campings":         [("tourism", "camp_site")],
    "bed-and-breakfasts": [("tourism", "guest_house")],
    "sportscholen":     [("leisure", "fitness_centre")],
    "kinderopvang":     [("amenity", "kindergarten"), ("amenity", "childcare")],
}

# zuid, west, noord, oost (grof; overlap is niet erg, dubbelen worden ontdubbeld op domein)
REGIOS = {
    "Drenthe":        (52.60, 6.10, 53.20, 7.10),
    "Groningen":      (52.95, 6.15, 53.55, 7.25),
    "Friesland":      (52.80, 5.35, 53.50, 6.45),
    "Overijssel":     (52.15, 5.75, 52.85, 7.10),
    "Gelderland":     (51.70, 5.00, 52.50, 6.85),
    "Flevoland":      (52.25, 5.15, 52.85, 5.95),
    "Utrecht":        (51.95, 4.75, 52.30, 5.65),
    "Noord-Holland":  (52.15, 4.50, 53.20, 5.35),
    "Zuid-Holland":   (51.70, 3.85, 52.35, 5.05),
    "Zeeland":        (51.20, 3.35, 51.80, 4.30),
    "Noord-Brabant":  (51.20, 4.20, 51.85, 6.05),
    "Limburg":        (50.75, 5.55, 51.80, 6.25),
    "Nederland":      (50.70, 3.30, 53.60, 7.25),
}
KETENS_BEKEND = {"intratuin.nl", "welkoop.nl", "groenrijk.nl", "boerenbond.nl", "praxis.nl", "gamma.nl",
                 "karwei.nl", "hornbach.nl", "tuincentrum.nl", "kwantum.nl", "hubo.nl", "formido.nl",
                 "jumbo.com", "ah.nl", "hema.nl", "kruidvat.nl", "etos.nl", "brezan.nl", "kwikfit.nl",
                 "halfords.nl", "profile.nl", "bakkerbart.nl", "subway.com", "mcdonalds.nl", "dominos.nl",
                 "newyorkpizza.nl", "kfc.nl", "burgerking.nl", "basic-fit.nl", "anytimefitness.nl",
                 "fitforfree.nl", "sportcity.nl", "kinderopvang.nl", "partou.nl", "kindergarden.nl",
                 "humankind.nl", "bakkerijbart.nl", "bakkerijvanmaanen.nl", "dekamarkt.nl", "plus.nl",
                 "coop.nl", "spar.nl", "jumbo.nl", "lidl.nl", "aldi.nl", "kapsalon.nl", "brainwash.nl",
                 "cosmo-hairstyling.nl", "kinki.nl", "teamkapsalon.nl", "hairstudio.nl", "toppers.nl",
                 "kappersbedrijf.nl", "nvm.nl", "funda.nl", "era.nl", "remax.nl", "hypotheker.nl",
                 "dierenkliniek.nl", "evidensia.nl", "anicura.nl", "dentconnect.nl", "dental-clinics.nl",
                 "fysioholland.nl", "cbi.nl", "anwb.nl", "vakgarage.nl", "bosch-car-service.nl",
                 "autofirst.nl", "carprof.nl", "profile.nl", "euromaster.nl", "bandenservice.nl"}


def tegels(bbox, stap=0.75):
    z, w, n, o = bbox
    lat = z
    while lat < n:
        lon = w
        while lon < o:
            yield (lat, lon, min(lat + stap, n), min(lon + stap, o))
            lon += stap
        lat += stap


def vraag(selectors, tegel):
    z, w, n, o = tegel
    regels = "".join(f'nwr["{k}"="{v}"]["website"]({z:.3f},{w:.3f},{n:.3f},{o:.3f});' for k, v in selectors)
    return f"[out:json][timeout:90];({regels});out center tags;"


def overpass(q, pogingen=2, timeout=150, log=None):
    """Vraagt de spiegels om de beurt; een HTML-antwoord (rate limit, runtime error) telt als
    mislukt en gaat door naar de volgende spiegel."""
    fout = None
    for i in range(pogingen):
        for url in SPIEGELS:
            try:
                data = urllib.parse.urlencode({"data": q}).encode()
                req = urllib.request.Request(url, data=data, headers={"User-Agent": "bouwstraat/1.0 (kapperstim@gmail.com)"})
                with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
                    ruw = r.read()
                if not ruw.lstrip().startswith(b"{"):
                    m = re.search(rb"Error</strong>: ([^<]{0,160})", ruw)
                    raise RuntimeError("overpass: " + (m.group(1).decode("utf-8", "ignore") if m else ruw[:120].decode("utf-8", "ignore")))
                d = json.loads(ruw.decode("utf-8"))
                if "remark" in d and "error" in d["remark"].lower() and not d.get("elements"):
                    raise RuntimeError("overpass: " + d["remark"][:160])
                return d
            except Exception as e:
                fout = e
                if log:
                    log(f"    {url.split('/')[2]}: {str(e)[:100]}")
                time.sleep(5 + i * 10)
    raise RuntimeError(f"Overpass niet bereikbaar: {str(fout)[:160]}")


def domein(url):
    url = url.strip()
    if not re.match(r"^https?://", url, re.I):
        url = "http://" + url
    host = urllib.parse.urlsplit(url).netloc.lower().split(":")[0]
    return re.sub(r"^www\.", "", host)


def hoofddomein(host):
    delen = host.split(".")
    return ".".join(delen[-2:]) if len(delen) >= 2 else host


def kwadranten(bbox):
    z, w, n, o = bbox
    mlat, mlon = (z + n) / 2, (w + o) / 2
    return [(z, w, mlat, mlon), (z, mlon, mlat, o), (mlat, w, n, mlon), (mlat, mlon, n, o)]


def oogst(branche, regio, maximum=1000, log=print):
    """Eén query voor het hele gebied (met website-filter duurt heel Nederland ±40 s);
    lukt dat niet, dan in vier kwadranten, en daarna pas in kleine tegels."""
    selectors = BRANCHES[branche]
    bbox = REGIOS[regio]
    gevonden = {}
    stukken = [bbox]
    try:
        t0 = time.time()
        d = overpass(vraag(selectors, bbox), pogingen=1, log=log)
        log(f"  hele regio in één keer: {len(d.get('elements', []))} elementen in {time.time()-t0:.0f} s")
        stukken = []
        batches = [d]
    except Exception as e:
        log(f"  hele regio lukte niet ({str(e)[:80]}); verder in kwadranten")
        batches = []
        stukken = kwadranten(bbox)
    for i, t in enumerate(stukken, 1):
        try:
            batches.append(overpass(vraag(selectors, t), pogingen=1, log=log))
            log(f"  deel {i}/{len(stukken)} klaar")
        except Exception as e:
            log(f"  deel {i}: lukte niet, overgeslagen: {str(e)[:60]}")
    for d in batches:
        for el in d.get("elements", []):
            tags = el.get("tags", {})
            web = tags.get("website") or tags.get("contact:website")
            if not web:
                continue
            for w in re.split(r"[;\s]+", web):
                if not w:
                    continue
                host = domein(w)
                if not host or "." not in host:
                    continue
                url = w if re.match(r"^https?://", w, re.I) else "http://" + w
                if host in gevonden:
                    continue
                centrum = el.get("center") or {"lat": el.get("lat"), "lon": el.get("lon")}
                gevonden[host] = {
                    "naam": tags.get("name") or tags.get("brand") or "",
                    "website": url, "domein": host,
                    "email": (tags.get("email") or tags.get("contact:email") or "").lower() or None,
                    "telefoon": tags.get("phone") or tags.get("contact:phone") or None,
                    "straat": " ".join(x for x in [tags.get("addr:street"), tags.get("addr:housenumber")] if x) or None,
                    "postcode": tags.get("addr:postcode"), "plaats": tags.get("addr:city"),
                    "lat": centrum.get("lat"), "lon": centrum.get("lon"),
                    "osm": f"{el.get('type')}/{el.get('id')}", "branche": branche, "regio": regio,
                    "tags": {k: v for k, v in tags.items() if k in ("craft", "shop", "amenity", "office", "healthcare", "tourism", "leisure", "brand")},
                }
                break
    # filters
    lijst = list(gevonden.values())
    voor = len(lijst)
    lijst = [b for b in lijst if b["domein"].endswith(".nl")]
    nl = len(lijst)
    teller = Counter(hoofddomein(b["domein"]) for b in lijst)
    ketens = {d for d, n in teller.items() if n > 2} | KETENS_BEKEND
    lijst = [b for b in lijst if hoofddomein(b["domein"]) not in ketens and not b["tags"].get("brand")]
    log(f"{branche} / {regio}: {voor} gevonden, {nl} met .nl-domein, {len(lijst)} na ketenfilter ({len(ketens & set(teller))} ketens)")
    return lijst


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--branche"); ap.add_argument("--regio")
    ap.add_argument("--uit"); ap.add_argument("--max", type=int, default=1000)
    ap.add_argument("--branches", action="store_true"); ap.add_argument("--regios", action="store_true")
    a = ap.parse_args()
    if a.branches:
        print("\n".join(BRANCHES)); return
    if a.regios:
        print("\n".join(REGIOS)); return
    lijst = oogst(a.branche, a.regio, a.max, log=lambda s: print(s, file=sys.stderr))
    tekst = json.dumps(lijst, ensure_ascii=False, indent=1)
    if a.uit:
        open(a.uit, "w", encoding="utf-8").write(tekst)
        print(f"{len(lijst)} bedrijven → {a.uit}", file=sys.stderr)
    else:
        print(tekst)


if __name__ == "__main__":
    main()
