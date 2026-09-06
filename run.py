#!/usr/bin/env python3
"""run.py — één site van begin tot eind: scan → uitlezen → foto's → bouwen → testen → (online).

    python3 run.py https://doelsite.nl [--map klanten/naam] [--branche hoveniers] [--deploy] [--demo-url URL]

Zonder --deploy blijft de demo lokaal (klanten/<map>/web). Met --deploy gaat hij naar
Cloudflare Pages (vereist CLOUDFLARE_API_TOKEN en CLOUDFLARE_ACCOUNT_ID).
Schrijft daarna de verkoopmail (mail.md / mail.json) op basis van de scan.
"""
import argparse, json, os, re, sys, time
import sitescan, extract, images, build, verify, mail


def slug(url):
    host = re.sub(r"^https?://", "", url.lower()).split("/")[0]
    host = re.sub(r"^www\.", "", host).split(":")[0]
    return re.sub(r"[^a-z0-9]+", "-", host.rsplit(".", 1)[0]).strip("-")[:40]


def vul_aan(c, aanvulling, log=print):
    """Ontbreekt adres of telefoon op de site, neem ze dan over uit OpenStreetMap (aanvulling uit
    de voorraad). Wordt gemarkeerd, zodat NALOPEN.md en het verslag melden dat het gecontroleerd moet worden."""
    if not aanvulling:
        return c
    if not (c.get("adres") or {}).get("plaats") and aanvulling.get("plaats"):
        pc = re.sub(r"^(\d{4})\s?([A-Za-z]{2})$", r"\1 \2", (aanvulling.get("postcode") or "").strip()).upper()
        c["adres"] = {"straat": aanvulling.get("straat") or "", "postcode": pc, "plaats": aanvulling["plaats"]}
        c["adres_bron"] = "openstreetmap"
        log("  adres niet op de site gevonden; overgenomen uit OpenStreetMap (controleren)")
    if not c.get("telefoon") and aanvulling.get("telefoon"):
        t = re.sub(r"\D", "", aanvulling["telefoon"])
        if t.startswith("31"):
            t = "0" + t[2:]
        if len(t) == 10:
            c["telefoon"] = [t]
            c["telefoon_bron"] = "openstreetmap"
            log("  telefoonnummer niet op de site gevonden; overgenomen uit OpenStreetMap (controleren)")
    return c


def alles(url, map_klant=None, branche=None, doe_deploy=False, demo_url=None, project="voorbeelden",
          prijs=750, maand=15, log=print, scan=None, naam_hint=None, config_pad=None, aanvulling=None, snel=False):
    t0 = time.time()
    map_klant = map_klant or os.path.join("klanten", slug(url))
    os.makedirs(map_klant, exist_ok=True)
    stappen = {}
    if scan is None:
        scan = sitescan.scan(url)
    json.dump(scan, open(os.path.join(map_klant, "scan.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    log(f"scan: {scan.get('score')} ({scan.get('klasse')})")
    if scan.get("fout"):
        raise RuntimeError(f"site niet bruikbaar: {scan['fout']}")
    c = extract.extract(scan.get("eind_url") or url, map_klant, branche, log=log, naam_hint=naam_hint)
    if not c.get("email") and scan.get("email"):
        c["email"] = scan["email"]
    vul_aan(c, aanvulling, log=log)
    json.dump(c, open(os.path.join(map_klant, "content.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    m = images.verwerk(map_klant, log=log)
    stappen["beelden"] = m.get("aantal_foto", 0)
    if not m.get("hero"):
        log("  let op: geen bruikbare foto voor de hero gevonden")
    build.bouw(map_klant, log=log)
    v = verify.verifieer(map_klant, log=log, snel=snel)
    stappen["verify_ok"] = v["ok"]
    url_demo = demo_url
    if doe_deploy:
        import deploy
        d = deploy.deploy(map_klant, project=project, log=log, config_pad=config_pad)
        url_demo = d["url"]
    if not url_demo:
        url_demo = "https://<demo-adres-nog-in-te-vullen>"
    mm = mail.schrijf(map_klant, scan, url_demo, prijs=prijs, maand=maand)
    stappen["mail_aan"] = mm["aan"]
    stappen["demo"] = url_demo
    stappen["seconden"] = round(time.time() - t0)
    log(f"klaar in {stappen['seconden']} s → {map_klant}")
    return {"map": map_klant, "scan": scan, "content": c, "images": m, "verify": v, "mail": mm, "demo": url_demo, "stappen": stappen}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("url"); ap.add_argument("--map"); ap.add_argument("--branche")
    ap.add_argument("--deploy", action="store_true"); ap.add_argument("--demo-url"); ap.add_argument("--project", default="voorbeelden")
    ap.add_argument("--prijs", type=int, default=750); ap.add_argument("--maand", type=int, default=15)
    a = ap.parse_args()
    r = alles(a.url, a.map, a.branche, a.deploy, a.demo_url, a.project, a.prijs, a.maand, log=lambda s: print(s, file=sys.stderr))
    print(json.dumps(r["stappen"], ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
