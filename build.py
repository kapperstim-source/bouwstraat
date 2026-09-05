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
import argparse, html, json, os, re, sys
from datetime import date
import teksten

E = lambda s: html.escape(str(s if s is not None else ""), quote=True)

CSS = """
*,*::before,*::after{box-sizing:border-box}
html{-webkit-text-size-adjust:100%;scroll-behavior:smooth}
@media (prefers-reduced-motion:reduce){html{scroll-behavior:auto}*{animation:none!important;transition:none!important}}
body{margin:0;font-family:system-ui,-apple-system,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif;color:var(--tekst);background:var(--wit);line-height:1.65;font-size:clamp(16px,1.05vw,17.5px)}
img{max-width:100%;height:auto;display:block}
a{color:var(--accent)}
h1,h2,h3{line-height:1.15;margin:0 0 .5em;letter-spacing:-.015em;font-weight:700}
h1{font-size:clamp(2rem,5.2vw,3.6rem)}h2{font-size:clamp(1.5rem,3vw,2.25rem)}h3{font-size:1.18rem}
p{margin:0 0 1em}
:root{--accent:ACCENT;--accent-d:ACCENTD;--tekst:#1c2118;--zacht:#555d52;--wit:#fff;--vel:#f6f5f1;--rand:#e3e2dc;--max:1180px;--r:14px}
.wrap{max-width:var(--max);margin:0 auto;padding:0 clamp(1rem,4vw,2rem)}
.knop{display:inline-block;background:var(--accent);color:#fff;text-decoration:none;font-weight:600;padding:.85em 1.6em;border-radius:999px;border:2px solid var(--accent);transition:background .15s,border-color .15s;cursor:pointer;font:inherit;font-weight:600}
.knop:hover{background:var(--accent-d);border-color:var(--accent-d)}
.knop--rand{background:transparent;color:var(--accent)}.knop--rand:hover{background:var(--accent);color:#fff}
.knop--licht{background:#fff;color:var(--accent-d);border-color:#fff}.knop--licht:hover{background:var(--vel);border-color:var(--vel);color:var(--accent-d)}
a:focus-visible,button:focus-visible,input:focus-visible,textarea:focus-visible{outline:3px solid var(--accent);outline-offset:3px;border-radius:4px}
.overslaan{position:absolute;left:-9999px}.overslaan:focus{position:static;display:inline-block;margin:.5rem;padding:.5rem 1rem;background:var(--accent);color:#fff}
.melding{background:#2c3330;color:#f2f4f1;font-size:.83rem;padding:.5rem 0}.melding a{color:#fff}
.melding .wrap{display:flex;gap:.6rem;flex-wrap:wrap;align-items:center;justify-content:center;text-align:center}
header.top{border-bottom:1px solid var(--rand);background:#fff;position:sticky;top:0;z-index:20}
header.top>.wrap{display:flex;align-items:center;justify-content:space-between;gap:1rem;flex-wrap:wrap;padding-top:.7rem;padding-bottom:.7rem}
.merk{display:flex;align-items:center;gap:.7rem;text-decoration:none;color:var(--tekst)}
.merk img{max-height:56px;width:auto}.merk b{font-size:1.05rem;line-height:1.2;display:block}.merk span{font-size:.8rem;color:var(--zacht)}
nav.hoofd{display:flex;gap:.3rem;align-items:center;flex-wrap:wrap}
nav.hoofd a{padding:.5em .85em;text-decoration:none;color:var(--tekst);border-radius:8px;font-weight:500}
nav.hoofd a:hover{background:var(--vel)}nav.hoofd a[aria-current=page]{color:var(--accent);font-weight:700}
nav.hoofd .knop{margin-left:.4rem;color:#fff}
.hero{position:relative;min-height:clamp(380px,58vh,560px);display:flex;align-items:flex-end;background:var(--accent-d);overflow:hidden}
.hero>img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover}
.hero::after{content:"";position:absolute;inset:0;background:linear-gradient(180deg,rgba(12,20,14,.15) 0%,rgba(12,20,14,.74) 100%)}
.hero .wrap{position:relative;z-index:2;color:#fff;padding-top:3.5rem;padding-bottom:3rem;width:100%}
.hero h1{color:#fff;max-width:16ch;text-shadow:0 2px 16px rgba(0,0,0,.35)}
.hero p{font-size:clamp(1.05rem,1.9vw,1.3rem);max-width:46ch;color:#f0f2ee;margin-bottom:1.6rem}
.hero .acties,.acties{display:flex;gap:.7rem;flex-wrap:wrap}
section{padding:clamp(3rem,7vw,5rem) 0}section.vel{background:var(--vel)}
.kop{max-width:60ch;margin-bottom:2.5rem}.kop p{color:var(--zacht);font-size:1.08rem;margin:0}
.rooster{display:grid;gap:1.4rem;grid-template-columns:repeat(auto-fit,minmax(min(100%,270px),1fr))}
.kaart{background:#fff;border:1px solid var(--rand);border-radius:var(--r);padding:1.6rem}
.kaart h3,.kaart h2{margin-bottom:.35rem;font-size:1.18rem}.kaart p{margin:0;color:var(--zacht);font-size:.97rem}
.kaart--vlak{background:transparent;border:0;padding:0}
.werk{display:grid;gap:1.2rem;grid-template-columns:repeat(auto-fit,minmax(min(100%,290px),1fr))}
figure.klus{margin:0;border-radius:var(--r);overflow:hidden;background:#fff;border:1px solid var(--rand)}
figure.klus img{aspect-ratio:4/3;object-fit:cover;width:100%;transition:transform .4s ease}figure.klus:hover img{transform:scale(1.04)}
figure.klus figcaption{padding:1rem 1.2rem;font-weight:600}
.galerij{display:grid;gap:.7rem;grid-template-columns:repeat(auto-fill,minmax(min(100%,190px),1fr))}
.galerij img{aspect-ratio:1;object-fit:cover;width:100%;border-radius:10px}
.strook{background:var(--accent);color:#fff}.strook h2{color:#fff}.strook a{color:#fff}.strook .knop--licht{color:var(--accent-d)}
.strook .wrap{display:flex;gap:2rem;flex-wrap:wrap;align-items:center;justify-content:space-between}.strook p{color:#fff;max-width:48ch;margin:0}
.gegevens{display:grid;gap:2rem;grid-template-columns:repeat(auto-fit,minmax(min(100%,260px),1fr));align-items:start}
dl{margin:0}.gegevens dt{font-weight:700;margin-top:1rem}.gegevens dd{margin:0;color:var(--zacht)}
.gegevens a{color:var(--accent);text-decoration:none;font-weight:600}.gegevens a:hover{text-decoration:underline}
.groot{font-size:1.5rem;font-weight:700}
form{display:grid;gap:1rem;max-width:44rem}.veld{display:grid;gap:.35rem}label{font-weight:600;font-size:.95rem}
input,textarea{font:inherit;padding:.7em .85em;border:1px solid var(--rand);border-radius:10px;background:#fff;color:var(--tekst);width:100%}
input:invalid:not(:placeholder-shown),textarea:invalid:not(:placeholder-shown){border-color:#b4261c}
.honing{position:absolute;left:-9999px;width:1px;height:1px;overflow:hidden}
.notitie{font-size:.9rem;color:var(--zacht);background:var(--vel);border-left:3px solid var(--accent);padding:.9rem 1.1rem;border-radius:0 8px 8px 0}
.intro{font-size:1.12rem;max-width:62ch}
footer.onder{background:#20261f;color:#c9cfc6;padding:3rem 0 2rem;font-size:.94rem}footer.onder a{color:#fff}
footer.onder .wrap{display:grid;gap:2rem;grid-template-columns:repeat(auto-fit,minmax(min(100%,220px),1fr))}
footer.onder h2{color:#fff;font-size:1rem;margin-bottom:.6rem}footer.onder p{margin:0 0 .35em}
.klein{font-size:.83rem;color:#aab3a6;border-top:1px solid #333c31;margin-top:2rem;padding-top:1.2rem}
.tekst{max-width:70ch}.tekst h2{font-size:1.3rem;margin-top:1.6em}
"""


def tel_mooi(t):
    t = re.sub(r"\D", "", t or "")
    if len(t) != 10:
        return t
    if t.startswith("06"):
        return f"{t[:2]} {t[2:4]} {t[4:6]} {t[6:8]} {t[8:]}"
    if t[:3] in ("010", "013", "020", "023", "024", "026", "030", "033", "035", "036", "038", "040", "043", "045", "046", "050", "053", "055", "058", "070", "071", "072", "073", "074", "075", "076", "077", "078", "079"):
        return f"{t[:3]} {t[3:6]} {t[6:]}"
    return f"{t[:4]} {t[4:7]} {t[7:]}"


def kop_html(c, m, pagina, afzender):
    naam = c["naam"]
    tel = c["telefoon"][0] if c.get("telefoon") else None
    logo = m.get("logo")
    if logo:
        merk = f'<a class="merk" href="./"><img src="{E(logo["bestand"])}" alt="Logo van {E(naam)}" width="{int(180 * logo["w"] / max(logo["w"], 1)) if logo["w"] <= 180 else 180}" height="{int(logo["h"] * (180 / logo["w"])) if logo["w"] > 180 else logo["h"]}" decoding="async"></a>'
    else:
        merk = f'<a class="merk" href="./"><b>{E(naam)}</b></a>'
    knop = f'<a class="knop" href="tel:{E(tel)}">{E(tel_mooi(tel))}</a>' if tel else '<a class="knop" href="contact">Contact</a>'
    def item(href, tekst, key):
        cur = ' aria-current="page"' if pagina == key else ""
        return f'<a href="{href}"{cur}>{tekst}</a>'
    return f"""<a class="overslaan" href="#inhoud">Naar de inhoud</a>
<div class="melding"><div class="wrap"><span>Voorbeeldontwerp voor {E(naam)} — gemaakt met tekst en foto's van de huidige website. Niet de officiële site.</span><span>· Voorstel van {E(afzender)}</span></div></div>
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


def pagina(c, m, titel, beschrijving, body, pagina_key, afzender, extra_head=""):
    accent = m.get("accent") or "#2f6b3a"
    accent_d = m.get("accent_donker") or "#22502b"
    css = CSS.replace("ACCENTD", accent_d).replace("ACCENT", accent)
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
<body>
{kop_html(c, m, pagina_key, afzender)}
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
    sub = c.get("intro") if c.get("intro") and len(c["intro"]) < 260 else t["sub"]
    diensten = teksten.koppel_diensten(c.get("diensten") or [], c.get("branche"))
    tel = c["telefoon"][0] if c.get("telefoon") else None
    mail = c.get("email")
    a = c.get("adres") or {}
    nalopen = []

    # ---------- index ----------
    hero = m.get("hero")
    hero_img = f'<img src="{E(hero["bestand"])}" width="{hero["w"]}" height="{hero["h"]}" alt="" fetchpriority="high" decoding="async">' if hero else ""
    acties = f'<a class="knop knop--licht" href="contact">{E(t["knop"])}</a>' + (f'<a class="knop" href="tel:{E(tel)}">Bel {E(tel_mooi(tel))}</a>' if tel else "")
    kaarten = "".join(f'<article class="kaart"><h3>{E(n)}</h3><p>{E(o)}</p></article>' for n, o, _ in diensten[:3])
    werk = ""
    if m.get("projecten"):
        figs = "".join(f'<figure class="klus"><img src="{E(p["beeld"])}" width="{p["w"]}" height="{p["h"]}" alt="{E(p["titel"])}" loading="lazy" decoding="async"><figcaption>{E(p["titel"])}</figcaption></figure>' for p in m["projecten"][:6])
        werk = f'<section><div class="wrap"><div class="kop"><h2>Uitgevoerd werk</h2><p>Een greep uit het werk dat op de huidige site staat.</p></div><div class="werk">{figs}</div></div></section>'
    waarom = "".join(f'<article class="kaart kaart--vlak"><h3>{E(k)}</h3><p>{E(x)}</p></article>' for k, x in t["waarom"])
    galerij = ""
    if m.get("galerij"):
        imgs = "".join(f'<img src="{E(g["bestand"])}" width="{g["w"]}" height="{g["h"]}" alt="" loading="lazy" decoding="async">' for g in m["galerij"][:8])
        galerij = f'<section><div class="wrap"><div class="kop"><h2>Beeld van het werk</h2></div><div class="galerij">{imgs}</div></div></section>'
    body = f"""
<div class="hero">{hero_img}<div class="wrap"><h1>{E(kop)}</h1><p>{E(sub)}</p><div class="acties">{acties}</div></div></div>
<section class="vel"><div class="wrap"><div class="kop"><h2>Wat we doen</h2><p>{E(t["diensten_intro"])}</p></div>
<div class="rooster">{kaarten}</div><p style="margin-top:2rem"><a class="knop knop--rand" href="diensten">Alle diensten bekijken</a></p></div></section>
{werk}
<section class="vel"><div class="wrap"><div class="kop"><h2>Waarom {E(naam)}</h2></div><div class="rooster">{waarom}</div></div></section>
{galerij}
<section class="strook"><div class="wrap"><div><h2>{E(t["cta"][0])}</h2><p>{E(t["cta"][1])}</p></div><div class="acties"><a class="knop knop--licht" href="contact">Neem contact op</a></div></div></section>"""
    schema = ""
    if a.get("plaats"):
        s = {"@context": "https://schema.org", "@type": "LocalBusiness", "name": naam,
             "address": {"@type": "PostalAddress", "streetAddress": a.get("straat") or "", "postalCode": a.get("postcode") or "", "addressLocality": a.get("plaats"), "addressCountry": "NL"}}
        if tel: s["telephone"] = tel
        if mail: s["email"] = mail
        schema = f'\n<script type="application/ld+json">{json.dumps(s, ensure_ascii=False)}</script>'
    open(os.path.join(web, "index.html"), "w", encoding="utf-8").write(
        pagina(c, m, f"{naam} — {kop}" if kop != naam else naam, sub, body, "index", afzender, schema))

    # ---------- diensten ----------
    kaarten = "".join(f'<article class="kaart"><h2>{E(n)}</h2><p>{E(o)}</p></article>' for n, o, _ in diensten)
    body = f"""
<section><div class="wrap"><div class="kop"><h1>Diensten</h1><p>{E(naam)}{" werkt in " + E(plaats) + " en omgeving." if plaats else "."} {E(t["diensten_intro"])}</p></div>
<div class="rooster">{kaarten}</div>
<p style="margin-top:2.5rem"><a class="knop" href="contact">{E(t["knop"])}</a></p></div></section>"""
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
    n.append(f"- Adres: {a.get('straat') or '—'}, {a.get('postcode') or ''} {a.get('plaats') or '—'}")
    n.append(f"- Telefoon: {', '.join(tel_mooi(x) for x in c.get('telefoon') or []) or '— NIET GEVONDEN'}")
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
    n.append("- Blok 'Waarom …': drie algemene punten, voorstel")
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
