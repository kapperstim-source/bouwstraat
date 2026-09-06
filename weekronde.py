#!/usr/bin/env python3
"""weekronde.py — de wekelijkse ronde: prospects kiezen, demo's bouwen, mailteksten maken.

    python3 weekronde.py --werkmap /tmp/ronde --administratie administratie.json \
        --kalender kalender.json [--config config.json] [--aantal 10] [--deploy] [--max-scan 120] [--test]

Leest de administratie (wie is al benaderd of overgeslagen), volgt de branchekalender,
haalt bedrijven uit de voorraad (--voorraad map met <branche>.json; anders live via
Overpass, wat traag en wisselvallig is) en scant nieuwe bedrijven tot er genoeg kansrijke prospects zijn, bouwt per prospect
een demo (extract → images → build → verify → deploy) en een mailtekst, en schrijft:

    <werkmap>/concepten.json      — per prospect: aan, onderwerp, tekst, demo, aandachtspunten
    <werkmap>/administratie.json  — bijgewerkte administratie (terugschrijven naar Drive!)
    <werkmap>/verslag.md          — leesbaar verslag van de ronde

De agent maakt daarna per concept een Gmail-concept aan. Verzenden doet Tim.
Zonder --deploy krijgen de demo's een tijdelijke placeholder-URL (alleen voor testen).
"""
import argparse, json, os, re, signal, sys, time, traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime
import oogst, sitescan, run

VANDAAG = date.today().isoformat()
MIN_SCORE = 40           # 'warm' en hoger; heet is 55+


LOGBESTAND = None


def log(s):
    regel = f"[{datetime.now():%H:%M:%S}] {s}"
    print(regel, file=sys.stderr, flush=True)
    if LOGBESTAND:
        with open(LOGBESTAND, "a", encoding="utf-8") as f:
            f.write(regel + "\n")


class Waakhond(Exception):
    pass


def _alarm(signum, frame):
    raise Waakhond("tijdslimiet van de hele ronde bereikt")


def laad(pad, standaard):
    try:
        return json.load(open(pad, encoding="utf-8"))
    except Exception:
        return standaard


def domein_van_mail(m):
    return (m or "").split("@")[-1].lower()


def in_administratie(adm, domein):
    return domein in adm["prospects"] or domein in adm["overgeslagen"]


def kies_kandidaten(scans, adm, aantal):
    """Rangschikt gescande bedrijven: score plus bonus voor aantoonbaar commercieel belang."""
    afgemeld = {a.lower() for a in adm.get("afgemeld", [])}
    kans = []
    for s in scans:
        if s.get("fout") or s.get("klasse") in ("onbereikbaar", "geparkeerd", "prima"):
            continue
        if s.get("platform"):
            continue            # zit vast aan Wix/Squarespace/…: slechte prospect
        if not s.get("email"):
            continue
        if s["email"].lower() in afgemeld or domein_van_mail(s["email"]) in afgemeld or s["domein"] in afgemeld:
            continue
        if s["score"] < MIN_SCORE:
            continue
        s["rang"] = s["score"] + 8 * len(s.get("belang") or [])
        kans.append(s)
    kans.sort(key=lambda s: -s["rang"])
    return kans


def reden_overslaan(s):
    """Korte code, zodat de administratie klein blijft: g=geparkeerd, z=gestopt/gesloten, x=onbereikbaar,
    p=platform (Wix e.d.), e=geen e-mail, s<score>=te lage score, a=afgemeld, b=bouw mislukt, m=te mager."""
    if s.get("geparkeerd"):
        return "g"
    if s.get("gestopt"):
        return "z"
    if s.get("fout"):
        return "x"
    if s.get("platform"):
        return "p"
    if not s.get("email"):
        return "e"
    if s["score"] < MIN_SCORE:
        return f"s{s['score']}"
    return "a"


def substantie(c, m):
    """Hoeveel er echt van het bedrijf zelf in de demo zit: logo, foto's, eigen introtekst, eigen
    dienstnamen, adres en telefoon van de site (niet uit OpenStreetMap)."""
    return sum([bool(m.get("logo")), (m.get("aantal_foto") or 0) >= 1, bool(c.get("intro")), bool(c.get("diensten")),
                bool((c.get("adres") or {}).get("plaats")) and c.get("adres_bron") != "openstreetmap",
                bool(c.get("telefoon")) and c.get("telefoon_bron") != "openstreetmap"])


def scan_alles(bedrijven, workers=12):
    uit = []
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(sitescan.scan, b["website"]): b for b in bedrijven}
        for i, f in enumerate(as_completed(futs), 1):
            b = futs[f]
            s = f.result()
            s["domein"] = b["domein"]; s["naam_osm"] = b.get("naam"); s["branche"] = b["branche"]
            s["plaats_osm"] = b.get("plaats"); s["email_osm"] = b.get("email")
            s["osm"] = {k: b.get(k) for k in ("straat", "postcode", "plaats", "telefoon") if b.get(k)}
            if not s.get("email") and b.get("email"):
                s["email"] = b["email"]
            uit.append(s)
            if i % 20 == 0:
                log(f"  gescand {i}/{len(bedrijven)}")
    return uit


def ronde(a):
    global LOGBESTAND
    t_start = time.time()
    os.makedirs(a.werkmap, exist_ok=True)
    LOGBESTAND = os.path.join(a.werkmap, "log.txt")
    open(LOGBESTAND, "w").close()
    # waakhond: wat er ook hangt (netwerk, browser, wrangler), na de tijdslimiet + 2 min
    # breken we af en schrijven we weg wat er is
    signal.signal(signal.SIGALRM, _alarm)
    signal.alarm(a.tijdslimiet + 120)
    log(f"start weekronde (limiet {a.tijdslimiet} s, aantal {a.aantal}, deploy {a.deploy})")
    adm = laad(a.administratie, {"stand": {"kalender_index": 0}, "prospects": {}, "overgeslagen": {}, "afgemeld": []})
    adm.setdefault("stand", {}).setdefault("kalender_index", 0)
    adm.setdefault("prospects", {}); adm.setdefault("overgeslagen", {}); adm.setdefault("afgemeld", [])
    kal = laad(a.kalender, {"ronden": [{"branche": "hoveniers", "regio": "Nederland"}]})
    ronden = kal["ronden"]
    cfg = laad(a.config, {}) if a.config else {}
    prijs = int(cfg.get("prijs", 750)); maand = int(cfg.get("maand", 15))
    project = cfg.get("pages_project", "voorbeelden")
    verslag = [f"# Weekronde {VANDAAG}", ""]

    # 1. kandidaten verzamelen via de kalender
    kandidaten = []
    gescand_nu = set()      # domeinen die deze ronde al gescand zijn (kansrijke staan nog niet in de administratie)
    idx = adm["stand"]["kalender_index"] % max(len(ronden), 1)
    bekeken = 0
    while len(kandidaten) < a.aantal + 2 and bekeken < min(3, len(ronden)):
        if time.time() - t_start > a.tijdslimiet * 0.6:
            log("meer dan 60% van de tijd op aan zoeken/scannen; door naar bouwen"); break
        r = ronden[idx]
        log(f"ronde: {r['branche']} / {r.get('regio', 'Nederland')}")
        lijst = None
        voorraad_pad = os.path.join(a.voorraad, f"{r['branche']}.json") if a.voorraad else None
        if voorraad_pad and os.path.exists(voorraad_pad):
            lijst = laad(voorraad_pad, [])
            if r.get("regio") and r["regio"] != "Nederland" and r["regio"] in oogst.REGIOS:
                z, w, n, o = oogst.REGIOS[r["regio"]]
                lijst = [b for b in lijst if b.get("lat") and z <= b["lat"] <= n and w <= b["lon"] <= o]
            log(f"  voorraad uit bestand: {len(lijst)} bedrijven")
        if lijst is None:
            try:
                lijst = oogst.oogst(r["branche"], r.get("regio", "Nederland"), log=log)
                if a.voorraad:
                    os.makedirs(a.voorraad, exist_ok=True)
                    json.dump(lijst, open(voorraad_pad, "w", encoding="utf-8"), ensure_ascii=False)
            except Exception as e:
                log(f"  oogst mislukt: {e}")
                verslag.append(f"- {r['branche']}: oogst mislukt ({str(e)[:80]})")
                lijst = []
        nieuw = [b for b in lijst if not in_administratie(adm, b["domein"]) and b["domein"] not in gescand_nu]
        log(f"  {len(lijst)} bedrijven, {len(nieuw)} nog niet bekeken")
        if not nieuw:
            verslag.append(f"- {r['branche']} / {r.get('regio', 'Nederland')}: alles al bekeken, door naar de volgende branche")
            idx = (idx + 1) % len(ronden); bekeken += 1
            adm["stand"]["kalender_index"] = idx
            continue
        nieuw = nieuw[: a.max_scan]
        try:
            scans = scan_alles(nieuw)
        except Waakhond:
            log("waakhond: afgebroken tijdens het scannen"); verslag.append("- waakhond: tijdslimiet bereikt tijdens het scannen"); break
        gescand_nu.update(b["domein"] for b in nieuw)
        goed = kies_kandidaten(scans, adm, a.aantal)
        for s in scans:
            if s not in goed:
                adm["overgeslagen"][s["domein"]] = reden_overslaan(s)
        al = {k["domein"] for k in kandidaten}
        kandidaten += [s for s in goed if s["domein"] not in al]
        verslag.append(f"- {r['branche']} / {r.get('regio', 'Nederland')}: {len(lijst)} gevonden, {len(nieuw)} gescand, {len(goed)} kansrijk (score ≥ {MIN_SCORE} met e-mail)")
        log(f"  {len(goed)} kansrijk")
        if len(nieuw) < a.max_scan:
            # deze ronde is (bijna) op: volgende keer verder met de volgende
            idx = (idx + 1) % len(ronden)
            adm["stand"]["kalender_index"] = idx
        bekeken += 1
    kandidaten.sort(key=lambda s: -s["rang"])
    if a.test:
        kandidaten = kandidaten[: max(a.aantal, 1)]

    # 2. demo's bouwen — een paar tegelijk (netwerk en browser wachten vooral), in vaste volgorde verwerkt
    concepten = []
    mislukt = []
    resultaten = {}

    def bouw_een(s):
        map_klant = os.path.join(a.werkmap, "klanten", run.slug(s["domein"]))
        regels = []
        try:
            uit = run.alles(s.get("eind_url") or s["url"], map_klant, s["branche"], doe_deploy=a.deploy, project=project,
                            prijs=prijs, maand=maand, log=regels.append, scan=s, naam_hint=s.get("naam_osm"), config_pad=a.config,
                            aanvulling=s.get("osm"), snel=a.snel)
            return s, uit, None, regels
        except Exception as e:
            return s, None, e, regels

    # in porties: eerst precies 'aantal', daarna alleen vervanging voor wat mislukte
    te_bouwen = []
    wachtrij = list(kandidaten)
    try:
        while True:
            nodig = a.aantal - sum(1 for d in te_bouwen if d["domein"] in resultaten and resultaten[d["domein"]][1] is None
                                   and substantie(resultaten[d["domein"]][0]["content"], resultaten[d["domein"]][0]["images"]) >= 2)
            portie = []
            while nodig > 0 and wachtrij:
                portie.append(wachtrij.pop(0)); nodig -= 1
            if not portie:
                break
            if time.time() - t_start > a.tijdslimiet:
                log("tijdslimiet bereikt, niet alle kandidaten gestart"); verslag.append("- tijdslimiet bereikt; niet alle kandidaten gebouwd")
                break
            te_bouwen += portie
            with ThreadPoolExecutor(max_workers=max(1, a.parallel)) as ex:
                futs = []
                for s in portie:
                    log(f"bouwen: {s['domein']} (score {s['score']}, belang {s.get('belang')})")
                    futs.append(ex.submit(bouw_een, s))
                for f in as_completed(futs):
                    s, uit, fout, regels = f.result()
                    for r in regels:
                        log(f"  [{s['domein']}] {r}")
                    resultaten[s["domein"]] = (uit, fout)
    except Waakhond:
        log("waakhond: afgebroken tijdens het bouwen; wat klaar is wordt weggeschreven")
        verslag.append("- waakhond: tijdslimiet bereikt tijdens het bouwen")

    for s in te_bouwen:
        if len(concepten) >= a.aantal:
            break
        if s["domein"] not in resultaten:
            continue
        uit, fout = resultaten[s["domein"]]
        if fout is not None:
            log(f"  mislukt: {s['domein']}: {fout}")
            mislukt.append((s["domein"], str(fout)[:120]))
            adm["overgeslagen"][s["domein"]] = "b"
            continue
        c, m, v, mm = uit["content"], uit["images"], uit["verify"], uit["mail"]
        if substantie(c, m) < 2:
            # te weinig van het bedrijf zelf (geen logo, geen foto's, geen eigen tekst): de demo is dan alleen sjabloon
            log(f"  te mager om te sturen: {s['domein']} (niets eigens gevonden)")
            mislukt.append((s["domein"], "te mager: geen logo, foto's of eigen tekst gevonden"))
            adm["overgeslagen"][s["domein"]] = "m"
            continue
        aandacht = []
        if not m.get("logo"): aandacht.append("geen logo gevonden — bedrijfsnaam staat als tekst")
        if not m.get("hero"): aandacht.append("geen bruikbare foto voor de kop")
        if (m.get("aantal_foto") or 0) < 3: aandacht.append(f"maar {m.get('aantal_foto', 0)} foto's bruikbaar")
        if not (c.get("adres") or {}).get("plaats"): aandacht.append("geen adres gevonden")
        elif c.get("adres_bron") == "openstreetmap": aandacht.append("adres komt uit OpenStreetMap, stond niet op hun site — controleren")
        if not c.get("telefoon"): aandacht.append("geen telefoonnummer gevonden")
        elif c.get("telefoon_bron") == "openstreetmap": aandacht.append("telefoonnummer komt uit OpenStreetMap, stond niet op hun site — controleren")
        if mm.get("aan") and s.get("domein") and domein_van_mail(mm["aan"]) != s["domein"]:
            aandacht.append(f"e-mailadres hoort bij een ander domein ({domein_van_mail(mm['aan'])}) — controleren of dit echt van dit bedrijf is")
        if not c.get("diensten"): aandacht.append("diensten zijn standaardteksten voor de branche (stonden niet op hun site)")
        if not v["ok"]: aandacht.append("verify niet helemaal schoon: " + json.dumps({k: v[k] for k in ("kapotte_links", "js_fouten", "axe_schendingen", "horizontale_scroll") if v[k]}, ensure_ascii=False)[:300])
        if not mm.get("aan"): aandacht.append("GEEN E-MAILADRES — concept niet aanmaken")
        if s.get("email") and c.get("email") and s["email"] != c["email"]: aandacht.append(f"scan vond ander adres: {s['email']}")
        concepten.append({
            "domein": s["domein"], "bedrijf": c["naam"], "plaats": (c.get("adres") or {}).get("plaats"), "branche": s["branche"],
            "score": s["score"], "belang": s.get("belang") or [], "aan": mm.get("aan"), "onderwerp": mm["onderwerp"], "tekst": mm["tekst"],
            "demo": uit["demo"], "punten": mm["punten"], "aandacht": aandacht, "map": uit["map"],
            "screenshot": os.path.join(uit["map"], "screens", "index-mobiel.png"), "seconden": uit["stappen"]["seconden"],
        })
        adm["prospects"][s["domein"]] = {"naam": c["naam"], "email": mm.get("aan"), "branche": s["branche"], "score": s["score"],
                                        "status": "concept", "datum": VANDAAG, "demo": uit["demo"], "onderwerp": mm["onderwerp"]}
    # 3. wegschrijven
    signal.alarm(0)
    adm["stand"]["laatste_ronde"] = VANDAAG
    adm["stand"]["aantal_ronden"] = adm["stand"].get("aantal_ronden", 0) + 1
    json.dump(adm, open(os.path.join(a.werkmap, "administratie.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    json.dump(concepten, open(os.path.join(a.werkmap, "concepten.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    verslag += ["", f"## {len(concepten)} concepten klaar", "",
                "Kop-foto, diensten en teksten zijn automatisch gekozen: bekijk elke demo even voordat je het concept verstuurt.", ""]
    for k in concepten:
        verslag.append(f"- **{k['bedrijf']}** ({k['plaats'] or '?'}, {k['branche']}, score {k['score']}) → {k['aan']} · demo {k['demo']}"
                       + (f" · let op: {'; '.join(k['aandacht'])}" if k["aandacht"] else ""))
    if mislukt:
        verslag += ["", "## Mislukt", ""] + [f"- {d}: {f}" for d, f in mislukt]
    verslag += ["", f"Duur: {round((time.time() - t_start) / 60)} min · administratie: {len(adm['prospects'])} benaderd, {len(adm['overgeslagen'])} overgeslagen, kalender-index {adm['stand']['kalender_index']}"]
    open(os.path.join(a.werkmap, "verslag.md"), "w", encoding="utf-8").write("\n".join(verslag) + "\n")
    open(os.path.join(a.werkmap, "klaar.txt"), "w").write(f"{datetime.now():%Y-%m-%d %H:%M:%S} klaar, {len(concepten)} concepten\n")
    print("\n".join(verslag))
    return concepten


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--werkmap", default="/tmp/ronde"); ap.add_argument("--administratie", required=True); ap.add_argument("--kalender", required=True)
    ap.add_argument("--config"); ap.add_argument("--aantal", type=int, default=10); ap.add_argument("--max-scan", type=int, default=120)
    ap.add_argument("--voorraad", help="map met <branche>.json uit oogst.py; ontbreekt een bestand, dan wordt live geoogst")
    ap.add_argument("--deploy", action="store_true"); ap.add_argument("--test", action="store_true")
    ap.add_argument("--tijdslimiet", type=int, default=25 * 60, help="seconden voor de hele ronde")
    ap.add_argument("--parallel", type=int, default=3, help="aantal demo's dat tegelijk gebouwd wordt")
    ap.add_argument("--snel", action="store_true", help="alleen screenshots van de homepage (controles blijven volledig)")
    a = ap.parse_args()
    ronde(a)


if __name__ == "__main__":
    main()
