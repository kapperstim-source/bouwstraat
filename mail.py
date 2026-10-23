#!/usr/bin/env python3
"""mail.py — stelt de verkoopmail samen uit de scan, de demo en de bouwgegevens.

    python3 mail.py klanten/<map> --scan scan.json --demo https://... [--prijs 750] [--maand 15] [--punt "iets wat je zelf zag"]

Schrijft klanten/<map>/mail.json {onderwerp, aan, tekst} en mail.md.
Opbouw (verkoopmail.md, positieve versie 22-10; aangepast 23-10): wie/waarom · compliment ·
schermafbeelding van de homepage (plek [[AFBEELDING …]]) · link op eigen domein <slug>.tdswebstudio.nl ·
wat u terugziet (fotobesparing als cijfer) · prijs eenmalig, geen maandbedrag · makkelijke uitweg ·
ondertekening met TDS Webstudio, tdswebstudio.nl en KvK-nummer.

Schrijft naast de platte tekst ook een HTML-versie (veld "html"). Het Gmail-concept is daarna nog
NIET af: de Gmail-koppeling schrijft elke link om naar google.com/url en kan geen afbeelding plaatsen.
De afwerkronde in Gmail (Claude in Chrome) zet de links terug en plakt de schermafbeelding op de plek
van PLEK. Zolang die tekst er nog staat, is het concept niet klaar om te versturen.
Onderwerp begint altijd met "Voorbeeld van een nieuwe website voor" — daar zoekt de
inbox-agent op. Over certificaten/https staat niets in de mail (niet te controleren).
"""
import argparse, json, os, re, sys

NIET_IN_MAIL = {"geen-https", "https-leeg", "https-placeholder", "geen-https-doorverwijzing", "mixed-content", "geen-canonical", "geen-schema", "html-groot"}
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
            "intro": "Mijn naam is Tim Kappers. Ik ben vierdejaars student commerciële economie en bouw websites voor ondernemers.",
            # Tim, 23-10: herkenbaar en controleerbaar wie er mailt (reactie Moerkerk over phishing)
            "bedrijf": "TDS Webstudio", "site": "tdswebstudio.nl", "kvk": "42129603"}

DOMEIN = "tdswebstudio.nl"   # <slug>.tdswebstudio.nl → Worker "voorbeeld-proxy" → <slug>.voorbeelden.pages.dev
PLEK = "[[AFBEELDING – eerst afwerken, nog niet versturen]]"


def nette_link(demo_url):
    """https://<slug>.voorbeelden.pages.dev → https://<slug>.tdswebstudio.nl (zelfde site, eigen domein)."""
    m = re.match(r"^https://([a-z0-9-]+)\.voorbeelden\.pages\.dev/?$", demo_url or "")
    return f"https://{m.group(1)}.{DOMEIN}" if m else demo_url


def naar_html(tekst, link, afzender=None):
    """Platte mailtekst → eenvoudige HTML zoals Gmail die zelf maakt (div per regel), met nette links."""
    import html as H
    afzender = afzender or AFZENDER
    kort = link.split("://", 1)[-1].rstrip("/")
    uit = []
    for alinea in tekst.strip("\n").split("\n\n"):
        regels = [H.escape(r, quote=False) for r in alinea.split("\n")]
        blok = "<br>".join(regels)
        if kort and kort in blok:
            blok = blok.replace(kort, f'<a href="{link}">{kort}</a>', 1)
        if afzender["site"] and blok.startswith(H.escape(afzender["naam"])):
            blok = blok.replace(f"· {afzender['site']}", f'· <a href="https://{afzender["site"]}">{afzender["site"]}</a>', 1)
            blok = blok.replace(afzender["email"], f'<a href="mailto:{afzender["email"]}">{afzender["email"]}</a>', 1)
        uit.append(f"<div>{blok}</div>")
    return "<div><br></div>".join(uit)


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
    # Positieve opbouw (Tim, 29-09 en 22-10): geen lijst met fouten, alleen wat het voorbeeld oplevert.
    beter = []
    if (m.get("besparing_pct") or 0) >= 25 and (m.get("origineel_mb") or 0) >= 1.0:
        beter.append(f"dezelfde foto's, maar {m['besparing_pct']} procent lichter, dus de site laadt op een telefoon veel sneller")
    else:
        beter.append("de site past zich aan elk scherm aan, of dat nu een telefoon, tablet of laptop is")
    if c.get("telefoon"):
        beter.append("uw telefoonnummer bovenaan elke pagina, met één tik te bellen")
    else:
        beter.append("op elke pagina een knop om direct contact op te nemen")
    beter.append("een eigen omschrijving voor Google, zodat u meer invloed heeft op wat mensen in de zoekresultaten lezen")
    beter_txt = "\n".join(f"- {z};" if i < len(beter) - 1 else f"- {z}." for i, z in enumerate(beter))
    # alleen beloven wat er echt in zit
    delen = ["uw eigen teksten"]
    if (m.get("aantal_foto") or 0) > 0:
        delen.append("foto's")
    if m.get("logo"):
        delen.append("logo")
    eigen = delen[0] if len(delen) == 1 else ", ".join(delen[:-1]) + " en " + delen[-1]
    onderwerp = f"Voorbeeld van een nieuwe website voor {naam}"
    link = nette_link(demo_url)
    kort = link.split("://", 1)[-1].rstrip("/")
    zoek = f" Toen ik naar {BRANCHE_WOORD.get(c.get('branche'), 'bedrijven')} rond {plaats} keek, kwam ik uw website tegen." if plaats else f" Toen ik naar {BRANCHE_WOORD.get(c.get('branche'), 'bedrijven')} keek, kwam ik uw website tegen."
    # Prijs (Tim, 22-10): alleen eenmalig, geen maandbedrag. --maand wordt niet meer gebruikt.
    tekst = f"""Beste heer/mevrouw,

{afzender['intro']}{zoek}

{eigen[0].upper() + eigen[1:]} zijn een mooie basis. Ik was benieuwd hoe dat eruit zou zien in een nieuw jasje, dus ik heb alvast een voorbeeld gemaakt. Zo ziet de homepage eruit:

{PLEK}

Het hele voorbeeld staat op mijn eigen website, zodat u het ook op uw telefoon kunt bekijken: {kort}

Wat u erin terugziet:
{beter_txt}

Het is een eerste opzet (er staat nog een balkje op dat het een voorbeeld is), en de teksten over uw diensten passen we samen aan.

Wat het kost: € {prijs} eenmalig voor de complete site. U krijgt alle bestanden mee. Met die bouwprijs zit ik onder wat freelancers (€ 800 tot € 4.000) en bureaus (€ 1.500 tot € 5.000) meestal rekenen, omdat ik mijn eerste opdrachten aan het opbouwen ben. U betaalt pas na oplevering en het domein blijft op uw naam.

Ik ben benieuwd wat u ervan vindt. U kunt gewoon op deze mail reageren. En heeft u er geen behoefte aan, laat het dan even weten, dan hoort u niets meer van mij.

Met vriendelijke groet,

{afzender['naam']}
{afzender['bedrijf']} · {afzender['site']}
KvK {afzender['kvk']}
{afzender['email']}
"""
    uit = {"onderwerp": onderwerp, "aan": aan, "tekst": tekst, "html": naar_html(tekst, link, afzender), "punten": punten,
           "demo": link, "demo_bron": demo_url, "bedrijf": naam}
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
