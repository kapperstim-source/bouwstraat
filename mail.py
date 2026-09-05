#!/usr/bin/env python3
"""mail.py — stelt de verkoopmail samen uit de scan, de demo en de bouwgegevens.

    python3 mail.py klanten/<map> --scan scan.json --demo https://... [--prijs 750] [--maand 15] [--punt "iets wat je zelf zag"]

Schrijft klanten/<map>/mail.json {onderwerp, aan, tekst} en mail.md.
Opbouw (verkoopmail.md): wie/waarom · drie concrete dingen · demo-link · wat beter is met
de fotobesparing als cijfer · prijs met marktvergelijking · makkelijke uitweg.
Onderwerp begint altijd met "Voorbeeld van een nieuwe website voor" — daar zoekt de
inbox-agent op. Over certificaten/https staat niets in de mail (niet te controleren).
"""
import argparse, json, os, re, sys

NIET_IN_MAIL = {"geen-https", "https-leeg", "geen-https-doorverwijzing", "mixed-content", "geen-canonical", "geen-schema", "html-groot"}
VOLGORDE = ["geen-viewport", "traag", "flash", "oude-html", "tabel-layout", "wordpress-oud", "copyright-oud", "beeld-zwaar",
            "geen-description", "geen-title", "jquery-oud", "alt-ontbreekt", "geen-og", "analytics-zonder-cookiemelding",
            "geen-privacy", "geen-h1", "geen-webp", "geen-lazy", "bootstrap-oud"]

BRANCHE_WOORD = {"hoveniers": "hoveniers", "tuincentra": "tuincentra", "dakdekkers": "dakdekkers", "timmerbedrijven": "timmerbedrijven",
                 "schilders": "schildersbedrijven", "installateurs": "installateurs", "stukadoors": "stukadoors", "tegelzetters": "tegelzetters",
                 "metselaars": "metselaars", "aannemers": "aannemers", "kappers": "kappers", "schoonheidssalons": "schoonheidssalons",
                 "fysiotherapeuten": "fysiotherapiepraktijken", "tandartsen": "tandartspraktijken", "dierenartsen": "dierenartsen",
                 "autogarages": "garages", "fietsenmakers": "fietsenmakers", "bakkers": "bakkers", "slagers": "slagers", "bloemisten": "bloemisten",
                 "rijscholen": "rijscholen", "makelaars": "makelaars", "restaurants": "restaurants", "cafes": "cafés", "campings": "campings",
                 "bed-and-breakfasts": "bed & breakfasts", "sportscholen": "sportscholen", "kinderopvang": "kinderopvang"}

AFZENDER = {"naam": "Tim Kappers", "email": "kapperstim@gmail.com",
            "intro": "Ik ben Tim Kappers, vierdejaars student commerciële economie, en ik bouw websites voor kleine bedrijven."}


def kies_punten(scan, punt_eigen=None, n=3):
    b = [x for x in scan.get("bevindingen", []) if x["code"] not in NIET_IN_MAIL]
    b.sort(key=lambda x: (VOLGORDE.index(x["code"]) if x["code"] in VOLGORDE else 99, -x["punten"]))
    zinnen = []
    if punt_eigen:
        zinnen.append(punt_eigen.strip().rstrip("."))
    for x in b:
        if len(zinnen) >= n:
            break
        zinnen.append(x["zin"].rstrip("."))
    return zinnen


def schrijf(map_klant, scan, demo_url, prijs=750, maand=15, punt=None, afzender=AFZENDER):
    c = json.load(open(os.path.join(map_klant, "content.json"), encoding="utf-8"))
    try:
        m = json.load(open(os.path.join(map_klant, "images.json"), encoding="utf-8"))
    except FileNotFoundError:
        m = {}
    naam = c["naam"]
    plaats = (c.get("adres") or {}).get("plaats")
    aan = c.get("email") or scan.get("email")
    punten = kies_punten(scan, punt)
    if not punten:
        punten = ["de site is op een telefoon lastig te lezen en te bedienen"]
    opsomming = "\n".join(f"- {z};" if i < len(punten) - 1 else f"- {z}." for i, z in enumerate(punten))
    beter = []
    if m.get("besparing_pct") and m.get("origineel_mb"):
        beter.append(f"dezelfde foto's wegen nu {m['origineel_mb']:.1f} MB en in het voorbeeld {m['webp_mb']:.1f} MB — {m['besparing_pct']} procent minder, dus veel sneller op een telefoon".replace(".", ","))
    beter.append("de site past zich aan het scherm aan, of dat nu een telefoon, tablet of laptop is")
    beter.append("het telefoonnummer staat op elke pagina bovenaan, met één tik te bellen")
    beter.append("de basis voor Google is op orde: titels, omschrijvingen en de bedrijfsgegevens in de code")
    beter_txt = "\n".join(f"- {z};" if i < len(beter) - 1 else f"- {z}." for i, z in enumerate(beter))
    onderwerp = f"Voorbeeld van een nieuwe website voor {naam}"
    tekst = f"""Beste heer/mevrouw,

{afzender['intro']} Ik kwam de website van {naam} tegen{f" toen ik naar {BRANCHE_WOORD.get(c.get('branche'), 'bedrijven')} rond {plaats} keek" if plaats else ''}, en ik zag een paar dingen die u waarschijnlijk klanten kosten:

{opsomming}

In plaats van dat alleen te vertellen heb ik een voorbeeld gemaakt van hoe uw site er nu uit zou kunnen zien, met uw eigen teksten, foto's en logo:

{demo_url}

Het is een voorstel, geen kopie: er staat nog een balkje op dat het een voorbeeld is, en de teksten over de diensten zijn een eerste opzet die we samen aanpassen. Wat er concreet beter is:

{beter_txt}

Wat het kost: € {prijs} eenmalig voor de complete site, en € {maand} per maand voor hosting, back-ups en kleine wijzigingen (die stuurt u gewoon per mail of app). Ter vergelijking: freelancers rekenen voor een eenvoudige zakelijke site doorgaans € 800 tot € 4.000 en bureaus € 1.500 tot € 5.000, met onderhoud vanaf € 50 per maand. Ik zit daar bewust onder omdat ik mijn eerste opdrachten aan het opbouwen ben. Het domein blijft op uw naam en u krijgt de bestanden mee als u dat wilt, dus u zit nergens aan vast.

Heeft u er geen behoefte aan, laat het dan even weten — dan hoort u niets meer van mij. Wilt u het voorbeeld liever eerst rustig bekijken, dan hoor ik het graag als ik u ergens mee kan helpen.

Met vriendelijke groet,

{afzender['naam']}
{afzender['email']}
"""
    uit = {"onderwerp": onderwerp, "aan": aan, "tekst": tekst, "punten": punten, "demo": demo_url, "bedrijf": naam}
    json.dump(uit, open(os.path.join(map_klant, "mail.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    open(os.path.join(map_klant, "mail.md"), "w", encoding="utf-8").write(f"Aan: {aan}\nOnderwerp: {onderwerp}\n\n{tekst}")
    return uit


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("map"); ap.add_argument("--scan", required=True); ap.add_argument("--demo", required=True)
    ap.add_argument("--prijs", type=int, default=750); ap.add_argument("--maand", type=int, default=15); ap.add_argument("--punt")
    a = ap.parse_args()
    scan = json.load(open(a.scan, encoding="utf-8"))
    uit = schrijf(a.map, scan, a.demo, a.prijs, a.maand, a.punt)
    print(f"Aan: {uit['aan']}\nOnderwerp: {uit['onderwerp']}\n\n{uit['tekst']}")


if __name__ == "__main__":
    main()
