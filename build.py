#!/usr/bin/env python3
"""build.py — bouwt uit content.json + images.json een demo van drie pagina's in
klanten/<map>/web/: index.html, diensten.html, contact.html (+ privacy.html, 404.html,
robots.txt). Schrijft ook NALOPEN.md: wat feit is en wat voorstel-tekst.

    python3 build.py klanten/<map> [--afzender "Tim Kappers"]

Elke pagina draagt boven- en onderaan een melding dat het een voorbeeldontwerp is, plus
noindex, zodat de demo niet met de echte site concurreert in Google.
Contactformulier: voorbeeldmodus (controleert invoer, verstuurt niets) tenzij
content.json een "formulier_endpoint" heeft. Honeypot-veld heet 'website'.
"""
import argparse, html, json, os, re, shutil, sys
from datetime import date
import teksten

E = lambda s: html.escape(str(s if s is not None else ""), quote=True)

import stijlen

BRANCHE_ENKEL = {"hoveniers": "hoveniersbedrijf", "tuincentra": "tuincentrum", "dakdekkers": "dakdekkersbedrijf", "schilders": "schildersbedrijf",
                 "timmerbedrijven": "timmerbedrijf", "installateurs": "installatiebedrijf", "stukadoors": "stukadoorsbedrijf", "kappers": "kapsalon",
                 "schoonheidssalons": "schoonheidssalon", "fysiotherapeuten": "fysiotherapiepraktijk", "autogarages": "autogarage", "bakkers": "bakkerij",
                 "restaurants": "restaurant", "rijscholen": "rijschool", "makelaars": "makelaardij", "bloemisten": "bloemist", "dierenartsen": "dierenartsenpraktijk",
                 "tandartsen": "tandartspraktijk", "fietsenmakers": "fietsenmaker", "slagers": "slagerij", "campings": "camping", "sportscholen": "sportschool",
                 "tegelzetters": "tegelzetbedrijf", "metselaars": "metselbedrijf", "aannemers": "aannemersbedrijf", "cafes": "café", "kinderopvang": "kinderopvang"}




def tel_mooi(t):
    t = re.sub(r"\D", "", t or "")
    if len(t) != 10:
        return t
    if t.startswith("06"):
        return f"{t[:2]} {t[2:4]} {t[4:6]} {t[6:8]} {t[8:]}"
    if t[:3] in ("010", "013", "020", "023", "024", "026", "030", "033", "035", "036", "038", "040", "043", "045", "046", "050", "053", "055", "058", "070", "071", "072", "073", "074", "075", "076", "077", "078", "079"):
        return f"{t[:3]} {t[3:6]} {t[6:]}"
    return f"{t[:4]} {t[4:7]} {t[7:]}"


def eerste_zin(t):
    m = re.match(r"(.+?[.!?])(\s|$)", t)
    z = (m.group(1) if m else t).strip()
    return z if len(z) <= 140 else ""


def knip(t, n):
    """Kort een tekst af op een zinseinde vóór n tekens."""
    if len(t) <= n:
        return t
    deel = t[:n]
    i = max(deel.rfind(". "), deel.rfind("! "), deel.rfind("? "))
    return (deel[:i + 1] if i > 60 else deel.rsplit(" ", 1)[0] + "…").strip()


def kop_html(c, m, pagina, afzender, tel_als_knop=True):
    naam = c["naam"]
    tel = c["telefoon"][0] if c.get("telefoon") else None
    logo = m.get("logo")
    if logo:
        merk = f'<a class="merk" href="./"><img src="{E(logo["bestand"])}" alt="Logo van {E(naam)}" width="{int(180 * logo["w"] / max(logo["w"], 1)) if logo["w"] <= 180 else 180}" height="{int(logo["h"] * (180 / logo["w"])) if logo["w"] > 180 else logo["h"]}" decoding="async"></a>'
    else:
        merk = f'<a class="merk" href="./"><b>{E(naam)}</b></a>'
    if tel and tel_als_knop:
        knop = f'<a class="knop" href="tel:{E(tel)}">{E(tel_mooi(tel))}</a>'
    elif tel:
        knop = f'<a class="tel" href="tel:{E(tel)}">{E(tel_mooi(tel))}</a>'
    else:
        knop = '<a class="knop" href="contact">Contact</a>'
    def item(href, tekst, key):
        cur = ' aria-current="page"' if pagina == key else ""
        return f'<a href="{href}"{cur}>{tekst}</a>'
    return f"""<a class="overslaan" href="#inhoud">Naar de inhoud</a>
<div class="melding"><div class="wrap"><span>Voorbeeldontwerp voor {E(naam)} door {E(afzender)}, met tekst{" en foto's" if (m.get("aantal_foto") or 0) else ""} van de huidige site. Niet de officiële website.</span></div></div>
<header class="top"><div class="wrap">
  {merk}
  <nav class="hoofd" aria-label="Hoofdmenu">{item("./", "Home", "index")}{item("diensten", "Diensten", "diensten")}{item("contact", "Contact", "contact")}{knop}</nav>
</div></header>
<main id="inhoud">"""


def voet_html(c):
    a = c.get("adres") or {}
    naam = c["naam"]
    tel = c["telefoon"][0] if c.get("telefoon") else None
    mail = c.get("email")
    soc = "".join(f'<p><a href="{E(u)}" rel="noopener">{k.capitalize()}</a></p>' for k, u in (c.get("socials") or {}).items())
    adres = "".join(f"<p>{E(x)}</p>" for x in [a.get("straat"), " ".join(y for y in [a.get("postcode"), a.get("plaats")] if y)] if x)
    return f"""</main>
<footer class="onder">
  <div class="wrap">
    <div><h2>{E(naam)}</h2>{adres}{f'<p>KvK {E(c["kvk"])}</p>' if c.get("kvk") else ""}</div>
    <div><h2>Contact</h2>{f'<p><a href="tel:{E(tel)}">{E(tel_mooi(tel))}</a></p>' if tel else ""}{f'<p><a href="mailto:{E(mail)}">{E(mail)}</a></p>' if mail else ""}{soc}</div>
    <div><h2>Pagina's</h2><p><a href="./">Home</a></p><p><a href="diensten">Diensten</a></p><p><a href="contact">Contact</a></p><p><a href="privacy">Privacy</a></p></div>
  </div>
  <div class="wrap"><p class="klein">© {date.today().year} {E(naam)} — voorbeeldontwerp, geen officiële website.</p></div>
</footer>"""


def pagina(c, m, titel, beschrijving, body, pagina_key, afzender, extra_head="", stijl=None):
    stijl = stijl or c.get("_stijl")
    naam_stijl, pal = stijl
    css = stijlen.css_voor(naam_stijl, pal)
    accent = pal["accent"]
    tel_als_knop = stijlen.STIJLEN[naam_stijl]["tel_als_knop"]
    return f"""<!doctype html>
<html lang="nl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{E(titel)}</title>
<meta name="description" content="{E(beschrijving)}">
<meta name="robots" content="noindex,nofollow">
<meta name="theme-color" content="{accent}">
<meta property="og:title" content="{E(titel)}"><meta property="og:description" content="{E(beschrijving)}">{extra_head}
<style>{css}</style>
</head>
<body class="stijl-{naam_stijl}">
{kop_html(c, m, pagina_key, afzender, tel_als_knop)}
{body}
{voet_html(c)}
</body>
</html>
"""


def bouw(map_klant, afzender="Tim Kappers", log=print):
    c = json.load(open(os.path.join(map_klant, "content.json"), encoding="utf-8"))
    try:
        m = json.load(open(os.path.join(map_klant, "images.json"), encoding="utf-8"))
    except FileNotFoundError:
        m = {"logo": None, "accent": None, "accent_donker": None, "hero": None, "projecten": [], "galerij": []}
    web = os.path.join(map_klant, "web")
    os.makedirs(web, exist_ok=True)
    t = teksten.voor(c.get("branche"))
    naam = c["naam"]
    plaats = (c.get("adres") or {}).get("plaats")
    kop = t["kop_plaats"].format(naam=naam, plaats=plaats) if plaats else t["kop"].format(naam=naam)
    intro = (c.get("intro") or "").strip()
    if intro and len(intro) < 260:
        sub, intro_lang = intro, ""
    else:
        sub = t["sub"]
        intro_lang = knip(intro, 420) if intro else ""
    intro_kort = eerste_zin(intro) if intro else ""
    intro_rest = knip(intro[len(intro_kort):].strip(), 300) if intro_kort and intro.startswith(intro_kort) else ""
    diensten = teksten.koppel_diensten(c.get("diensten") or [], c.get("branche"))
    tel = c["telefoon"][0] if c.get("telefoon") else None
    mail = c.get("email")
    a = c.get("adres") or {}

    # stijl kiezen (voorspelbaar per domein) en lettertypes meeleveren
    naam_stijl, pal = stijlen.kies(c.get("domein") or naam, m, voorkeur=c.get("stijl"))
    c["_stijl"] = (naam_stijl, pal)
    os.makedirs(os.path.join(web, "fonts"), exist_ok=True)
    for f in stijlen.fontbestanden(naam_stijl):
        shutil.copy(os.path.join(stijlen.HIER, "vendor", "fonts", f), os.path.join(web, "fonts", f))
    ctx = dict(naam=naam, plaats=plaats, kop=kop, sub=sub, intro_kort=intro_kort, intro_rest=intro_rest, intro_lang=intro_lang, diensten=diensten,
               tel=tel, tel_mooi=tel_mooi(tel) if tel else "", mail=mail, adres=a, hero=m.get("hero"), galerij=m.get("galerij") or [],
               projecten=m.get("projecten") or [], t=t, branche_woord=BRANCHE_ENKEL.get(c.get("branche") or "", ""),
               logo=m.get("logo"), socials=c.get("socials") or {})

    # ---------- index ----------
    body = "\n".join(blok(ctx) for blok in stijlen.STIJLEN[naam_stijl]["volgorde"])
    schema = ""
    if a.get("plaats"):
        sd = {"@context": "https://schema.org", "@type": "LocalBusiness", "name": naam,
              "address": {"@type": "PostalAddress", "streetAddress": a.get("straat") or "", "postalCode": a.get("postcode") or "", "addressLocality": a.get("plaats"), "addressCountry": "NL"}}
        if tel: sd["telephone"] = tel
        if mail: sd["email"] = mail
        schema = f'\n<script type="application/ld+json">{json.dumps(sd, ensure_ascii=False)}</script>'
    open(os.path.join(web, "index.html"), "w", encoding="utf-8").write(
        pagina(c, m, f"{naam} — {kop}" if kop != naam else naam, sub, body, "index", afzender, schema))

    # ---------- diensten ----------
    if naam_stijl in ("fris", "strak"):
        lijst = '<div class="rooster">' + "".join(f'<article class="kaart"><h2>{E(n)}</h2><p>{E(o)}</p></article>' for n, o, _ in diensten) + "</div>"
    else:
        lijst = '<div class="dienstlijst">' + "".join(f'<article><h3>{E(n)}</h3><p>{E(o)}</p></article>' for n, o, _ in diensten) + "</div>"
    werkwijze = "".join(f"<p><b>{E(k)}.</b> {E(x)}</p>" for k, x in t["waarom"])
    body = f"""
<section><div class="wrap"><div class="kop"><h1>Diensten</h1><p>{E(naam)}{" werkt in " + E(plaats) + " en omgeving." if plaats else "."} {E(t["diensten_intro"])}</p></div>
{lijst}
<div class="tekst" style="margin-top:3rem"><h2 style="font-size:1.25rem">Zo werken we</h2>{werkwijze}</div>
<p style="margin-top:2rem"><a class="knop" href="contact">{E(t["knop"])}</a></p></div></section>"""
    open(os.path.join(web, "diensten.html"), "w", encoding="utf-8").write(
        pagina(c, m, f"Diensten — {naam}", f"Wat {naam} voor u kan doen.", body, "diensten", afzender))

    # ---------- contact ----------
    endpoint = c.get("formulier_endpoint")
    adres_html = "".join(f"<dt>{k}</dt><dd>{v}</dd>" for k, v in [
        ("Telefoon", f'<span class="groot"><a href="tel:{E(tel)}">{E(tel_mooi(tel))}</a></span>' if tel else None),
        ("E-mail", f'<a href="mailto:{E(mail)}">{E(mail)}</a>' if mail else None),
        ("Adres", (E(a["straat"]) + "<br>" if a.get("straat") else "") + E(" ".join(x for x in [a.get("postcode"), a.get("plaats")] if x)) if a.get("plaats") else None),
        ("KvK", E(c["kvk"]) if c.get("kvk") else None)] if v)
    kaart_link = ""
    if a.get("straat") and a.get("plaats"):
        q = html.escape("+".join((a["straat"] + ", " + (a.get("postcode") or "") + " " + a["plaats"]).split()))
        kaart_link = f'<p><a href="https://www.openstreetmap.org/search?query={q}" rel="noopener">Bekijk op de kaart</a></p>'
    avg = (f"Uw gegevens gaan rechtstreeks naar {E(mail)} en worden alleen gebruikt om uw vraag te beantwoorden." if mail
           else "Uw gegevens worden alleen gebruikt om uw vraag te beantwoorden.")
    body = f"""
<section><div class="wrap"><div class="kop"><h1>Contact</h1><p>Bel, mail of laat hieronder uw gegevens achter.</p></div>
<div class="gegevens">
  <div><dl>{adres_html}</dl>{kaart_link}</div>
  <div>
    <form id="aanvraag" novalidate{f' action="{E(endpoint)}" method="post"' if endpoint else ""}>
      <div class="veld"><label for="v-naam">Naam</label><input id="v-naam" name="naam" required autocomplete="name" placeholder="Uw naam"></div>
      <div class="veld"><label for="v-mail">E-mailadres</label><input id="v-mail" name="email" type="email" required autocomplete="email" placeholder="naam@voorbeeld.nl"></div>
      <div class="veld"><label for="v-tel">Telefoon <span style="font-weight:400;color:var(--zacht)">(optioneel)</span></label><input id="v-tel" name="telefoon" type="tel" autocomplete="tel" placeholder="06 12 34 56 78"></div>
      <div class="veld"><label for="v-bericht">Waar kunnen we mee helpen?</label><textarea id="v-bericht" name="bericht" rows="5" required placeholder="Vertel kort wat u zoekt"></textarea></div>
      <div class="honing" aria-hidden="true"><label for="v-website">Website</label><input id="v-website" name="website" tabindex="-1" autocomplete="off"></div>
      <div><button class="knop" type="submit">Versturen</button></div>
      <p id="uitkomst" role="status" class="notitie" hidden></p>
      <p class="notitie" style="font-size:.85rem">{avg} Zie ook de <a href="privacy">privacyverklaring</a>.</p>
    </form>
    {"" if endpoint else '<p class="notitie" style="margin-top:1rem">Dit is een voorbeeldpagina. Het formulier controleert de invoer wel, maar verstuurt nog niets — daar hoort een mailkoppeling achter.</p>'}
  </div>
</div></div></section>
<script>
(function(){{
  var f=document.getElementById('aanvraag'),uit=document.getElementById('uitkomst'),knop=f.querySelector('button');
  var endpoint={json.dumps(endpoint or "")},tel={json.dumps(tel_mooi(tel) if tel else "")},mail={json.dumps(mail or "")};
  f.addEventListener('submit',function(e){{
    e.preventDefault();
    if(f.website&&f.website.value){{return;}}
    if(!f.checkValidity()){{var eerste=f.querySelector(':invalid');if(eerste)eerste.focus();uit.hidden=false;uit.textContent='Vul de gemarkeerde velden nog even aan.';return;}}
    if(!endpoint){{uit.hidden=false;uit.textContent='Bedankt, uw bericht is gecontroleerd. In de echte versie komt het nu binnen'+(mail?' op '+mail:'')+'.';return;}}
    knop.disabled=true;var oud=knop.textContent;knop.textContent='Bezig…';
    var fd=new FormData(f);
    fetch(endpoint,{{method:'POST',body:fd,headers:{{'Accept':'application/json'}}}}).then(function(r){{
      if(!r.ok)throw new Error(r.status);
      f.reset();uit.hidden=false;uit.textContent='Bedankt, uw bericht is verstuurd. We nemen contact met u op.';
    }}).catch(function(){{
      uit.hidden=false;uit.textContent='Het versturen is niet gelukt.'+(tel?' Bel gerust even: '+tel+'.':' Probeer het later nog eens.');
    }}).finally(function(){{knop.disabled=false;knop.textContent=oud;}});
  }});
}})();
</script>"""
    open(os.path.join(web, "contact.html"), "w", encoding="utf-8").write(
        pagina(c, m, f"Contact — {naam}", f"Neem contact op met {naam}" + (f" in {plaats}" if plaats else "") + ".", body, "contact", afzender))

    # ---------- privacy ----------
    body = f"""
<section><div class="wrap tekst"><h1>Privacyverklaring</h1>
<p>{E(naam)} gaat zorgvuldig om met uw gegevens. Hieronder staat in het kort welke gegevens we verwerken en waarom.</p>
<h2>Contactformulier</h2><p>Vult u het contactformulier in, dan ontvangen we uw naam, e-mailadres, eventueel uw telefoonnummer en uw bericht. We gebruiken die gegevens alleen om uw vraag te beantwoorden en bewaren ze niet langer dan daarvoor nodig is.</p>
<h2>Geen tracking</h2><p>Deze website plaatst geen volgcookies en gebruikt geen advertentienetwerken. Er wordt geen bezoekersgedrag doorgegeven aan derden.</p>
<h2>Uw rechten</h2><p>U kunt ons vragen welke gegevens we van u hebben en om die te corrigeren of te verwijderen.{f' Stuur daarvoor een bericht naar <a href="mailto:{E(mail)}">{E(mail)}</a>.' if mail else ''}</p>
<p class="notitie">Dit is een voorbeeldtekst bij een voorbeeldontwerp; de definitieve verklaring wordt met de ondernemer afgestemd.</p>
</div></section>"""
    open(os.path.join(web, "privacy.html"), "w", encoding="utf-8").write(pagina(c, m, f"Privacy — {naam}", "Privacyverklaring.", body, "privacy", afzender))
    body = '<section><div class="wrap tekst"><h1>Pagina niet gevonden</h1><p>Deze pagina bestaat niet (meer). <a href="./">Terug naar de homepage</a>.</p></div></section>'
    open(os.path.join(web, "404.html"), "w", encoding="utf-8").write(pagina(c, m, f"Niet gevonden — {naam}", "Pagina niet gevonden.", body, "404", afzender))
    open(os.path.join(web, "robots.txt"), "w").write("User-agent: *\nDisallow: /\n")

    # ---------- NALOPEN ----------
    n = [f"# Nalopen — {naam}", "", f"Bron: {c.get('bron_url')} · gebouwd {date.today():%d-%m-%Y}", "",
         "## Feiten (overgenomen van de huidige site — controleer of ze kloppen)", ""]
    n.append(f"- Bedrijfsnaam: {naam}")
    n.append(f"- Adres: {a.get('straat') or '—'}, {a.get('postcode') or ''} {a.get('plaats') or '—'}" + (" — UIT OPENSTREETMAP, stond niet op hun site: controleren" if c.get("adres_bron") == "openstreetmap" else ""))
    n.append(f"- Telefoon: {', '.join(tel_mooi(x) for x in c.get('telefoon') or []) or '— NIET GEVONDEN'}" + (" — UIT OPENSTREETMAP, stond niet op hun site: controleren" if c.get("telefoon_bron") == "openstreetmap" else ""))
    n.append(f"- E-mail: {mail or '— NIET GEVONDEN'}")
    n.append(f"- KvK: {c.get('kvk') or '— niet gevonden'}")
    n.append(f"- Social: {', '.join(c.get('socials') or {}) or '—'}")
    n.append(f"- Logo: {'overgenomen (' + m['logo']['bron'] + ')' if m.get('logo') else '— NIET GEVONDEN, bedrijfsnaam als tekst gebruikt'}")
    n.append(f"- Foto's: {m.get('aantal_foto', 0)} overgenomen van de huidige site ({m.get('origineel_mb')} MB → {m.get('webp_mb')} MB als WebP)")
    n.append(f"- Projecten met titel én foto van hun site: {len(m.get('projecten') or [])}")
    n += ["", "## Voorstel-tekst (door ons geschreven, over het vak — niet over dit bedrijf)", ""]
    n.append(f"- Kop op de homepage: \"{kop}\"")
    n.append(f"- Onderregel: \"{sub}\"" + (" (overgenomen van hun site)" if sub == c.get("intro") else " (voorstel)"))
    for naam_d, oms, bron in diensten:
        n.append(f"- Dienst \"{naam_d}\": {'naam van hun site, omschrijving voorstel' if bron == 'site+voorstel' else 'naam van hun site, omschrijving neutraal' if bron == 'site' else 'volledig voorstel (stond niet op hun site)'}")
    n.append("- Blok 'Zo werken we' (dienstenpagina): drie algemene punten, voorstel")
    n.append(f"- Huisstijl: {naam_stijl} (automatisch gekozen; andere keuze: \"stijl\" in content.json)")
    n.append("- Privacyverklaring: voorbeeldtekst")
    n += ["", "## Nog te regelen voordat dit een echte site wordt", "",
          "- Formulier koppelen (formulier_endpoint in content.json, bijv. Formcarry) — nu voorbeeldmodus",
          "- Melding 'voorbeeldontwerp' en noindex weghalen", "- Teksten en foto's laten goedkeuren door de ondernemer",
          "- Openingstijden, certificaten, jaartallen: alleen toevoegen als de ondernemer ze aanlevert"]
    open(os.path.join(map_klant, "NALOPEN.md"), "w", encoding="utf-8").write("\n".join(n) + "\n")
    log(f"  gebouwd: index, diensten, contact, privacy, 404 → {web}")
    return web


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("map"); ap.add_argument("--afzender", default="Tim Kappers")
    a = ap.parse_args()
    bouw(a.map, a.afzender, log=lambda s: print(s, file=sys.stderr))


if __name__ == "__main__":
    main()
