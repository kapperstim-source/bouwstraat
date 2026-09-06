"""stijlen.py — vijf uiteenlopende huisstijlen voor de demo's, zodat niet elke demo hetzelfde
sjabloon is. Per stijl: lettertypes (meegeleverd, zie fonts.py), een paar kleurenpaletten,
eigen CSS en eigen opbouw van de homepage (kop, diensten, over, beeld, afsluiting).

De keuze is voorspelbaar (hash van het domein), zodat een demo bij opnieuw bouwen dezelfde
stijl houdt. Met "stijl" in content.json is hij te overrulen: "klassiek", "robuust", "fris",
"editorial" of "strak". Zonder foto's vallen de foto-afhankelijke stijlen af.
"""
import hashlib, html, os, re

E = lambda s: html.escape(str(s if s is not None else ""), quote=True)
HIER = os.path.dirname(os.path.abspath(__file__))


# ---------- kleur ----------
def rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def hexs(c):
    return "#%02x%02x%02x" % tuple(max(0, min(255, int(round(x)))) for x in c)


def meng(a, b, t):
    """t=0 → a, t=1 → b"""
    ra, rb = rgb(a), rgb(b)
    return hexs(tuple(ra[i] + (rb[i] - ra[i]) * t for i in range(3)))


def lum(h):
    def k(v):
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = rgb(h)
    return 0.2126 * k(r) + 0.7152 * k(g) + 0.0722 * k(b)


def contrast(a, b):
    la, lb = lum(a), lum(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def donker(h, t=0.25):
    return meng(h, "#000000", t)


def leesbaar_op_wit(accent):
    """Accent zo nodig donkerder maken tot tekst erin/erop ≥ 4.6:1 haalt tegen wit."""
    c = accent
    for _ in range(12):
        if contrast(c, "#ffffff") >= 4.6:
            return c
        c = donker(c, 0.12)
    return c


# ---------- gedeelde CSS ----------
BASIS = """
*,*::before,*::after{box-sizing:border-box}
html{-webkit-text-size-adjust:100%;scroll-behavior:smooth}
@media (prefers-reduced-motion:reduce){html{scroll-behavior:auto}*{animation:none!important;transition:none!important}}
body{margin:0;font-family:var(--tekstfont);color:var(--ink);background:var(--papier);line-height:1.6;font-size:clamp(16px,1.02vw,17.5px)}
img{max-width:100%;height:auto;display:block}
a{color:var(--accent)}
h1,h2,h3{font-family:var(--kopfont);line-height:1.12;margin:0 0 .5em;font-weight:var(--kopgewicht,700);letter-spacing:var(--kopspatie,-.01em)}
h1{font-size:var(--h1,clamp(2.1rem,5vw,3.6rem))}h2{font-size:var(--h2,clamp(1.5rem,3vw,2.2rem))}h3{font-size:var(--h3,1.15rem)}
p{margin:0 0 1em}
.wrap{max-width:var(--max,1140px);margin:0 auto;padding:0 clamp(1rem,4vw,2rem)}
.knop{display:inline-block;background:var(--accent);color:#fff;text-decoration:none;font-weight:600;padding:.8em 1.5em;border-radius:var(--knopr,6px);border:2px solid var(--accent);cursor:pointer;font:inherit;font-weight:600;line-height:1.2}
.knop:hover{background:var(--accent-d);border-color:var(--accent-d)}
.knop--rand{background:transparent;color:var(--accent)}.knop--rand:hover{background:var(--accent);color:#fff}
.knop--licht{background:#fff;color:var(--accent-d);border-color:#fff}.knop--licht:hover{background:var(--papier);border-color:var(--papier);color:var(--accent-d)}
.pijl{font-weight:600;text-decoration:none;color:var(--accent);border-bottom:2px solid currentColor;padding-bottom:.1em}.pijl:hover{color:var(--accent-d)}
a:focus-visible,button:focus-visible,input:focus-visible,textarea:focus-visible{outline:3px solid var(--accent);outline-offset:3px;border-radius:4px}
.overslaan{position:absolute;left:-9999px}.overslaan:focus{position:static;display:inline-block;margin:.5rem;padding:.5rem 1rem;background:var(--accent);color:#fff}
.melding{background:#2b2d2a;color:#eef0ea;font-size:.8rem;padding:.45rem 0;font-family:system-ui,sans-serif}.melding a{color:#fff}
.melding .wrap{display:flex;gap:.6rem;flex-wrap:wrap;align-items:center;justify-content:center;text-align:center}
header.top{background:var(--kopbalk,var(--papier));border-bottom:1px solid var(--rand)}
header.top>.wrap{display:flex;align-items:center;justify-content:space-between;gap:1rem;flex-wrap:wrap;padding-top:.8rem;padding-bottom:.8rem}
.merk{display:flex;align-items:center;gap:.7rem;text-decoration:none;color:var(--ink)}
.merk img{max-height:58px;width:auto}.merk b{font-family:var(--kopfont);font-size:1.25rem;line-height:1.15;display:block;font-weight:var(--kopgewicht,700)}
nav.hoofd{display:flex;gap:.2rem;align-items:center;flex-wrap:wrap}
nav.hoofd a{padding:.5em .8em;text-decoration:none;color:var(--ink);font-weight:500}
nav.hoofd a:hover{color:var(--accent)}nav.hoofd a[aria-current=page]{color:var(--accent);font-weight:700}
nav.hoofd .knop{margin-left:.5rem;color:#fff}nav.hoofd .tel{margin-left:.6rem;font-weight:700;color:var(--ink);text-decoration:none;white-space:nowrap}
section{padding:clamp(2.8rem,6.5vw,5rem) 0}
.eyebrow{font-size:.78rem;letter-spacing:.14em;text-transform:uppercase;font-weight:700;color:var(--accent);margin:0 0 .8em;font-family:var(--tekstfont)}
.kop{max-width:60ch;margin-bottom:2.2rem}.kop p{color:var(--zacht);font-size:1.06rem;margin:0}
.intro{font-size:1.1rem;max-width:62ch}
.acties{display:flex;gap:.8rem 1.4rem;flex-wrap:wrap;align-items:center}
.werk{display:grid;gap:1.2rem;grid-template-columns:repeat(auto-fit,minmax(min(100%,280px),1fr))}
figure.klus{margin:0;overflow:hidden;background:var(--vel);border-radius:var(--r,6px)}
figure.klus img{aspect-ratio:4/3;object-fit:cover;width:100%}
figure.klus figcaption{padding:.9rem 1.1rem;font-weight:600}
.gegevens{display:grid;gap:2rem;grid-template-columns:repeat(auto-fit,minmax(min(100%,260px),1fr));align-items:start}
dl{margin:0}.gegevens dt{font-weight:700;margin-top:1rem}.gegevens dd{margin:0;color:var(--zacht)}
.gegevens a{color:var(--accent);text-decoration:none;font-weight:600}.gegevens a:hover{text-decoration:underline}
.groot{font-size:1.5rem;font-weight:700}
form{display:grid;gap:1rem;max-width:44rem}.veld{display:grid;gap:.35rem}label{font-weight:600;font-size:.95rem}
input,textarea{font:inherit;padding:.7em .85em;border:1px solid var(--rand);border-radius:var(--r,6px);background:#fff;color:var(--ink);width:100%}
input:invalid:not(:placeholder-shown),textarea:invalid:not(:placeholder-shown){border-color:#b4261c}
.honing{position:absolute;left:-9999px;width:1px;height:1px;overflow:hidden}
.notitie{font-size:.9rem;color:var(--zacht);background:var(--vel);border-left:3px solid var(--accent);padding:.9rem 1.1rem}
.lijst{list-style:none;margin:0;padding:0}
.feiten{display:grid;gap:.2rem 1.5rem;grid-template-columns:auto 1fr;font-size:.98rem}.feiten dt{font-weight:700}.feiten dd{margin:0}
.feiten a{color:var(--ink);text-decoration:none}.feiten a:hover{text-decoration:underline}
footer.onder{background:var(--voetbg,#22251f);color:var(--voettekst,#cfd3c8);padding:2.6rem 0 1.8rem;font-size:.94rem}footer.onder a{color:#fff}
footer.onder .wrap{display:grid;gap:2rem;grid-template-columns:repeat(auto-fit,minmax(min(100%,220px),1fr))}
footer.onder h2{color:#fff;font-size:1rem;margin-bottom:.6rem;font-family:var(--tekstfont)}footer.onder p{margin:0 0 .35em}
.klein{font-size:.84rem;border-top:1px solid rgba(255,255,255,.15);margin-top:2rem;padding-top:1.2rem}
.tekst{max-width:70ch}.tekst h2{font-size:1.3rem;margin-top:1.6em}
.dienstlijst{display:grid;gap:1.6rem 2.5rem;grid-template-columns:repeat(auto-fit,minmax(min(100%,300px),1fr))}
.dienstlijst article h3{margin-bottom:.3rem}.dienstlijst article p{margin:0;color:var(--zacht)}
.rooster{display:grid;gap:1.3rem;grid-template-columns:repeat(auto-fit,minmax(min(100%,270px),1fr))}
.kaart{background:var(--kaartbg,#fff);border:1px solid var(--rand);border-radius:var(--r,6px);padding:1.5rem}
.kaart h2,.kaart h3{font-size:1.15rem;margin-bottom:.3rem}.kaart p{margin:0;color:var(--zacht);font-size:.97rem}
"""


def _foto(f, attrs="", lazy=True):
    if not f:
        return ""
    laad = ' loading="lazy"' if lazy else ' fetchpriority="high"'
    return f'<img src="{E(f["bestand"])}" width="{f["w"]}" height="{f["h"]}" alt="{E(f.get("alt") or "")}"{laad} decoding="async"{attrs}>'


def _tel_link(ctx, klas="pijl", tekst=None):
    if not ctx["tel"]:
        return ""
    return f'<a class="{klas}" href="tel:{E(ctx["tel"])}">{E(tekst or ("Bel " + ctx["tel_mooi"]))}</a>'


def _werk(ctx):
    if not ctx["projecten"]:
        return ""
    figs = "".join(f'<figure class="klus">{_foto(dict(p, bestand=p["beeld"], alt=p["titel"]))}<figcaption>{E(p["titel"])}</figcaption></figure>' for p in ctx["projecten"][:6])
    return f'<section class="werksectie"><div class="wrap"><p class="eyebrow">Uitgevoerd werk</p><h2>Een greep uit het werk</h2><div class="werk">{figs}</div></div></section>'


def _adres_regels(ctx):
    a = ctx["adres"]
    uit = []
    if a.get("straat"):
        uit.append(a["straat"])
    if a.get("plaats"):
        uit.append(" ".join(x for x in [a.get("postcode"), a.get("plaats")] if x))
    return uit


def _feiten(ctx, met_kaart=True):
    items = []
    regels = _adres_regels(ctx)
    if regels:
        items.append(("Adres", "<br>".join(E(r) for r in regels)))
    if ctx["tel"]:
        items.append(("Telefoon", f'<a href="tel:{E(ctx["tel"])}">{E(ctx["tel_mooi"])}</a>'))
    if ctx["mail"]:
        items.append(("E-mail", f'<a href="mailto:{E(ctx["mail"])}">{E(ctx["mail"])}</a>'))
    for k, u in (ctx["socials"] or {}).items():
        items.append((k.capitalize(), f'<a href="{E(u)}" rel="noopener">{E(u.split("/")[-1] or k)}</a>'))
    if not items:
        return ""
    return '<dl class="feiten">' + "".join(f"<dt>{k}</dt><dd>{v}</dd>" for k, v in items) + "</dl>"


# ====================================================================================
# STIJL A — klassiek: papier, serif-koppen, genummerde diensten, ingelijste foto
# ====================================================================================
KLASSIEK_CSS = """
:root{--kopfont:'Fraunces',Georgia,'Times New Roman',serif;--tekstfont:'Work Sans',system-ui,sans-serif;--kopgewicht:600;--kopspatie:-.02em;--knopr:3px;--r:4px;--h1:clamp(2.4rem,5.4vw,4rem)}
header.top{border-bottom:3px double var(--rand);background:var(--papier)}
header.top>.wrap{flex-direction:column;justify-content:center;gap:.4rem;padding-top:1.3rem;padding-bottom:.9rem}
.merk b{font-size:1.6rem}nav.hoofd a{letter-spacing:.06em;text-transform:uppercase;font-size:.82rem;font-weight:600}
.knop{text-transform:uppercase;letter-spacing:.08em;font-size:.86rem;padding:.9em 1.7em}
.hero-a{padding:clamp(2.5rem,6vw,5rem) 0}
.hero-a .wrap{display:grid;gap:clamp(2rem,5vw,4rem);grid-template-columns:repeat(auto-fit,minmax(min(100%,320px),1fr));align-items:center}
.hero-a h1{max-width:14ch}.hero-a .intro{font-size:1.15rem}
.lijst-a{position:relative}.lijst-a img{aspect-ratio:4/3;object-fit:cover;width:100%;border:6px solid #fff;box-shadow:12px 12px 0 var(--accent)}
.hero-a--tekst{text-align:center}.hero-a--tekst .wrap{display:block;max-width:820px}.hero-a--tekst h1{max-width:none;margin:0 auto .4em}.hero-a--tekst .intro{margin:0 auto 1.5rem}.hero-a--tekst .acties{justify-content:center}
.hero-a--tekst::before{content:"";display:block;width:64px;height:4px;background:var(--accent);margin:0 auto 1.6rem}
.nummers{list-style:none;margin:0;padding:0;display:grid;gap:0 3rem;grid-template-columns:repeat(auto-fit,minmax(min(100%,300px),1fr));counter-reset:d}
.nummers li{counter-increment:d;border-top:1px solid var(--rand);padding:1.3rem 0 1.3rem 3.2rem;position:relative}
.nummers li::before{content:counter(d,decimal-leading-zero);position:absolute;left:0;top:1.35rem;font-family:var(--kopfont);font-size:1.4rem;color:var(--accent);font-weight:600}
.nummers h3{margin-bottom:.25rem}.nummers p{margin:0;color:var(--zacht)}
.over-a .wrap{display:grid;gap:3rem;grid-template-columns:repeat(auto-fit,minmax(min(100%,300px),1fr));align-items:start}
.over-a{background:#fff;border-top:1px solid var(--rand);border-bottom:1px solid var(--rand)}
.galerij-a{display:grid;gap:.8rem;grid-template-columns:repeat(6,1fr)}
.galerij-a img{width:100%;height:100%;object-fit:cover;aspect-ratio:1}
.galerij-a img:first-child{grid-column:span 4;grid-row:span 2;aspect-ratio:auto}.galerij-a img:nth-child(n+2){grid-column:span 2}
@media (max-width:640px){.galerij-a{grid-template-columns:repeat(2,1fr)}.galerij-a img:first-child{grid-column:span 2;grid-row:auto;aspect-ratio:4/3}.galerij-a img:nth-child(n+2){grid-column:span 1}}
.slot-a{text-align:center;background:var(--papier)}.slot-a .groot{font-family:var(--kopfont);font-size:clamp(1.8rem,4vw,2.8rem);font-weight:600}.slot-a .groot a{color:var(--ink);text-decoration:none}.slot-a .groot a:hover{color:var(--accent)}
footer.onder{--voetbg:var(--ink)}
"""
KLASSIEK_PALETTEN = [
    dict(accent="#2f5d3a", papier="#f8f5ee", ink="#1e2320", zacht="#5b6058", rand="#dcd7cb", vel="#efeadf"),
    dict(accent="#7a2e2b", papier="#faf6f0", ink="#231f1e", zacht="#615a57", rand="#e1d9cf", vel="#f1e9df"),
    dict(accent="#223a5e", papier="#f6f5f1", ink="#1c2029", zacht="#585d69", rand="#d9d8d1", vel="#ebeae3"),
    dict(accent="#4b5d2a", papier="#f7f6ef", ink="#20241a", zacht="#5b6150", rand="#dbd9cc", vel="#ecebdf"),
]


def klassiek_hero(ctx):
    eyebrow = f'<p class="eyebrow">{E(ctx["branche_woord"])}{" · " + E(ctx["plaats"]) if ctx["plaats"] else ""}</p>' if ctx["branche_woord"] else ""
    acties = f'<div class="acties"><a class="knop" href="contact">{E(ctx["t"]["knop"])}</a>{_tel_link(ctx)}</div>'
    if ctx["hero"]:
        return f'<div class="hero-a"><div class="wrap"><div>{eyebrow}<h1>{E(ctx["naam"])}</h1><p class="intro">{E(ctx["sub"])}</p>{acties}</div><div class="lijst-a">{_foto(ctx["hero"], lazy=False)}</div></div></div>'
    return f'<div class="hero-a hero-a--tekst"><div class="wrap">{eyebrow}<h1>{E(ctx["naam"])}</h1><p class="intro">{E(ctx["sub"])}</p>{acties}</div></div>'


def klassiek_diensten(ctx):
    li = "".join(f"<li><h3>{E(n)}</h3><p>{E(o)}</p></li>" for n, o, _ in ctx["diensten"][:6])
    return f'<section><div class="wrap"><p class="eyebrow">Diensten</p><h2>{E(ctx["t"].get("diensten_kop", "Waar u voor bij ons terechtkunt"))}</h2><ol class="nummers">{li}</ol><p style="margin-top:1.8rem"><a class="pijl" href="diensten">Alle diensten →</a></p></div></section>'


def klassiek_over(ctx):
    tekst = E(ctx["intro_lang"] or ctx["t"]["sub"])
    return f'<section class="over-a"><div class="wrap"><div><p class="eyebrow">Over {E(ctx["naam"])}</p><p class="intro">{tekst}</p></div><div>{_feiten(ctx)}</div></div></section>'


def klassiek_galerij(ctx):
    g = ctx["galerij"]
    if len(g) < 3:
        return ""
    return f'<section><div class="wrap"><div class="galerij-a">{"".join(_foto(x) for x in g[:5])}</div></div></section>'


def klassiek_slot(ctx):
    tel = f'<p class="groot"><a href="tel:{E(ctx["tel"])}">{E(ctx["tel_mooi"])}</a></p>' if ctx["tel"] else ""
    return f'<section class="slot-a"><div class="wrap"><h2>{E(ctx["t"]["cta"][0])}</h2><p class="intro" style="margin:0 auto 1rem">{E(ctx["t"]["cta"][1])}</p>{tel}<p><a class="knop" href="contact">Neem contact op</a></p></div></section>'


# ====================================================================================
# STIJL B — robuust: condensed koppen in kapitalen, harde vlakken, foto met tekstpaneel
# ====================================================================================
ROBUUST_CSS = """
:root{--kopfont:'Barlow Condensed','Arial Narrow',sans-serif;--tekstfont:'Barlow',system-ui,sans-serif;--kopgewicht:700;--kopspatie:0;--knopr:0;--r:0;--h1:clamp(2.8rem,7vw,5.2rem);--h2:clamp(1.8rem,3.6vw,2.7rem)}
h1,h2{text-transform:uppercase;line-height:1}
header.top{border-top:6px solid var(--accent);border-bottom:2px solid var(--ink);position:sticky;top:0;z-index:20}
nav.hoofd a{text-transform:uppercase;font-family:var(--kopfont);font-size:1.05rem;font-weight:600;letter-spacing:.03em}
.knop{text-transform:uppercase;font-family:var(--kopfont);font-size:1.1rem;letter-spacing:.04em;padding:.7em 1.5em}
.hero-b{position:relative;background:var(--ink);color:#fff;overflow:hidden}
.hero-b>img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;opacity:.92}
.hero-b .wrap{position:relative;z-index:2;padding-top:clamp(3rem,9vw,7rem);padding-bottom:clamp(3rem,9vw,7rem)}
.paneel{background:var(--accent);color:#fff;padding:clamp(1.5rem,4vw,2.6rem);max-width:600px;box-shadow:0 0 0 1px rgba(0,0,0,.08)}
.paneel h1{color:#fff;margin-bottom:.35em}.paneel p{color:#fff;font-size:1.1rem;margin-bottom:1.3rem}
.paneel .knop{background:#fff;color:var(--accent-d);border-color:#fff}.paneel .knop:hover{background:var(--papier);border-color:var(--papier)}
.paneel .tel-groot{font-family:var(--kopfont);font-size:1.6rem;font-weight:700;color:#fff;text-decoration:none;text-transform:uppercase}
.hero-b--vlak{background:var(--accent)}.hero-b--vlak .paneel{background:transparent;max-width:760px;padding:0;box-shadow:none}
.hero-b--vlak .wrap{border-left:12px solid var(--ink)}
.strook-b{background:var(--ink);color:#fff;padding:1rem 0;font-family:var(--kopfont);font-size:1.15rem;text-transform:uppercase;letter-spacing:.04em}
.strook-b .wrap{display:flex;gap:.6rem 2.5rem;flex-wrap:wrap}
.diensten-b{display:grid;gap:0 2.5rem;grid-template-columns:repeat(auto-fit,minmax(min(100%,290px),1fr))}
.diensten-b article{border-top:3px solid var(--ink);padding:1.1rem 0 1.4rem}
.diensten-b h3{font-size:1.5rem;text-transform:uppercase;margin-bottom:.2rem}.diensten-b p{margin:0;color:var(--zacht)}
.over-b{background:var(--ink);color:#e8e8e4}.over-b h2{color:#fff}.over-b .intro{color:#fff;font-size:1.25rem}
.over-b .wrap{display:grid;gap:2.5rem;grid-template-columns:2fr 1fr}.over-b .feiten dt{color:#fff}.over-b .feiten a{color:#fff}
@media (max-width:760px){.over-b .wrap{grid-template-columns:1fr}}
.galerij-b{display:grid;gap:.5rem;grid-template-columns:repeat(auto-fill,minmax(min(100%,200px),1fr))}.galerij-b img{aspect-ratio:1;object-fit:cover;width:100%}
.slot-b{background:var(--accent);color:#fff}.slot-b h2{color:#fff}.slot-b p{color:#fff}
.slot-b .wrap{display:flex;gap:2rem;flex-wrap:wrap;align-items:center;justify-content:space-between}
footer.onder{--voetbg:#151617}
"""
ROBUUST_PALETTEN = [
    dict(accent="#b8401b", papier="#ffffff", ink="#1b1d1f", zacht="#54585c", rand="#d9dadb", vel="#f2f2f0"),
    dict(accent="#1f5f8b", papier="#ffffff", ink="#161b21", zacht="#4f5862", rand="#d5d9dd", vel="#eff2f4"),
    dict(accent="#2c6e49", papier="#ffffff", ink="#171b18", zacht="#51574f", rand="#d6d9d4", vel="#eff2ed"),
    dict(accent="#8a3b1e", papier="#fffdf9", ink="#1d1a17", zacht="#5c5650", rand="#dcd7d1", vel="#f3efe9"),
]


def robuust_hero(ctx):
    tel = f'<p><a class="tel-groot" href="tel:{E(ctx["tel"])}">Bel {E(ctx["tel_mooi"])}</a></p>' if ctx["tel"] else ""
    paneel = f'<div class="paneel"><h1>{E(ctx["kop"])}</h1><p>{E(ctx["sub"])}</p><div class="acties"><a class="knop" href="contact">{E(ctx["t"]["knop"])}</a></div>{tel}</div>'
    if ctx["hero"]:
        return f'<div class="hero-b">{_foto(ctx["hero"], lazy=False)}<div class="wrap">{paneel}</div></div>'
    return f'<div class="hero-b hero-b--vlak"><div class="wrap">{paneel}</div></div>'


def robuust_strook(ctx):
    delen = [E(n) for n, _, _ in ctx["diensten"][:5]]
    if ctx["plaats"]:
        delen.append(E(ctx["plaats"]) + " en omgeving")
    return f'<div class="strook-b"><div class="wrap">{"".join(f"<span>{d}</span>" for d in delen)}</div></div>'


def robuust_diensten(ctx):
    arts = "".join(f"<article><h3>{E(n)}</h3><p>{E(o)}</p></article>" for n, o, _ in ctx["diensten"][:6])
    return f'<section><div class="wrap"><h2>Dit doen we</h2><div class="diensten-b">{arts}</div><p style="margin-top:1.5rem"><a class="knop knop--rand" href="diensten">Alle diensten</a></p></div></section>'


def robuust_over(ctx):
    return f'<section class="over-b"><div class="wrap"><div><h2>{E(ctx["naam"])}</h2><p class="intro">{E(ctx["intro_lang"] or ctx["t"]["sub"])}</p></div><div>{_feiten(ctx)}</div></div></section>'


def robuust_galerij(ctx):
    g = ctx["galerij"]
    if len(g) < 3:
        return ""
    return f'<section><div class="wrap"><div class="galerij-b">{"".join(_foto(x) for x in g[:8])}</div></div></section>'


def robuust_slot(ctx):
    return f'<section class="slot-b"><div class="wrap"><div><h2>{E(ctx["t"]["cta"][0])}</h2><p>{E(ctx["t"]["cta"][1])}</p></div><a class="knop knop--licht" href="contact">Neem contact op</a></div></section>'


# ====================================================================================
# STIJL C — fris: ronde vormen, zachte tinten, fotomozaïek, één familie (Nunito)
# ====================================================================================
FRIS_CSS = """
:root{--kopfont:'Nunito',system-ui,sans-serif;--tekstfont:'Nunito',system-ui,sans-serif;--kopgewicht:800;--kopspatie:-.015em;--knopr:999px;--r:18px;--h1:clamp(2.2rem,5vw,3.6rem)}
header.top{border-bottom:0}
nav.hoofd a{border-radius:999px;font-weight:700}nav.hoofd a:hover{background:var(--tint)}
.hero-c{padding:clamp(1.5rem,4vw,3.5rem) 0 clamp(2.5rem,5vw,4rem)}
.hero-c .wrap{display:grid;gap:clamp(1.5rem,4vw,3.5rem);grid-template-columns:repeat(auto-fit,minmax(min(100%,320px),1fr));align-items:center}
.hero-c h1{max-width:15ch}.hero-c .intro{font-size:1.15rem}
.mozaiek{display:grid;gap:.7rem;grid-template-columns:1fr 1fr}
.mozaiek img{width:100%;height:100%;object-fit:cover;border-radius:var(--r);aspect-ratio:1}
.mozaiek img:first-child{grid-column:span 2;aspect-ratio:16/10}
.enkel img{border-radius:var(--r);aspect-ratio:4/3;object-fit:cover;width:100%}
.hero-c--vlak .wrap{display:block}.hero-c--vlak .blok{background:var(--tint);border-radius:calc(var(--r) * 1.6);padding:clamp(2rem,6vw,4.5rem)}.hero-c--vlak h1{max-width:18ch}
.chips{display:flex;flex-wrap:wrap;gap:.5rem;margin:0 0 2rem;padding:0;list-style:none}
.chips li{background:var(--tint);color:var(--accent-d);border-radius:999px;padding:.4em 1em;font-weight:700;font-size:.92rem}
.diensten-c{display:grid;gap:1.2rem;grid-template-columns:repeat(auto-fit,minmax(min(100%,280px),1fr))}
.diensten-c article{background:var(--tint);border-radius:var(--r);padding:1.5rem 1.6rem}
.diensten-c h3{margin-bottom:.3rem}.diensten-c p{margin:0;color:var(--zacht)}
.quote-c{background:var(--accent);color:#fff;border-radius:calc(var(--r) * 1.6)}
.quote-c .wrap{padding-top:clamp(2rem,5vw,3.5rem);padding-bottom:clamp(2rem,5vw,3.5rem)}
.quote-c p{font-family:var(--kopfont);font-size:clamp(1.3rem,2.6vw,1.9rem);font-weight:700;line-height:1.35;max-width:30ch;margin:0}
.quote-c .wie{font-size:1rem;font-weight:700;opacity:.85;margin-top:1.2rem;font-family:var(--tekstfont)}
.rond{max-width:var(--max);margin:0 auto;padding:0 clamp(1rem,4vw,2rem)}
.galerij-c{display:grid;gap:.8rem;grid-template-columns:repeat(auto-fill,minmax(min(100%,180px),1fr))}.galerij-c img{aspect-ratio:1;object-fit:cover;width:100%;border-radius:var(--r)}
.slot-c{background:var(--tint);border-radius:calc(var(--r) * 1.6);padding:clamp(2rem,5vw,3.5rem);display:flex;gap:2rem;flex-wrap:wrap;align-items:center;justify-content:space-between}
.slot-c h2{margin-bottom:.3rem}.slot-c p{margin:0;color:var(--zacht)}
.over-c .wrap{display:grid;gap:2.5rem;grid-template-columns:repeat(auto-fit,minmax(min(100%,280px),1fr))}
footer.onder{--voetbg:var(--accent-d);--voettekst:#f2f5f2;border-radius:calc(var(--r) * 1.6) calc(var(--r) * 1.6) 0 0}
"""
FRIS_PALETTEN = [
    dict(accent="#1f7a8c", papier="#ffffff", ink="#172026", zacht="#4f5b63", rand="#dfe5e8", vel="#f1f6f7"),
    dict(accent="#c94f2f", papier="#fffdfb", ink="#241c18", zacht="#5f544d", rand="#e8ded8", vel="#faf1ec"),
    dict(accent="#2e7d3a", papier="#ffffff", ink="#18211a", zacht="#4f5a51", rand="#dbe4dc", vel="#f0f6f0"),
    dict(accent="#2b62b0", papier="#ffffff", ink="#161c26", zacht="#4f5868", rand="#dbe1ec", vel="#eff3fa"),
    dict(accent="#7b4b94", papier="#ffffff", ink="#1e1823", zacht="#5a5061", rand="#e4dde9", vel="#f5f0f8"),
]


def fris_hero(ctx):
    acties = f'<div class="acties"><a class="knop" href="contact">{E(ctx["t"]["knop"])}</a>{_tel_link(ctx)}</div>'
    tekst = f'<div><h1>{E(ctx["kop"])}</h1><p class="intro">{E(ctx["sub"])}</p>{acties}</div>'
    g = ctx["galerij"]
    if ctx["hero"] and len(g) >= 3:
        fotos = [ctx["hero"]] + [x for x in g if x["bestand"] != ctx["hero"]["bestand"]][:2]
        return f'<div class="hero-c"><div class="wrap">{tekst}<div class="mozaiek">{"".join(_foto(f, lazy=(i > 0)) for i, f in enumerate(fotos))}</div></div></div>'
    if ctx["hero"]:
        return f'<div class="hero-c"><div class="wrap">{tekst}<div class="enkel">{_foto(ctx["hero"], lazy=False)}</div></div></div>'
    return f'<div class="hero-c hero-c--vlak"><div class="wrap"><div class="blok">{tekst}</div></div></div>'


def fris_quote(ctx):
    if not ctx["intro_lang"]:
        return ""
    return f'<div class="rond"><div class="quote-c"><div class="wrap"><p>“{E(ctx["intro_lang"])}”</p><p class="wie">— {E(ctx["naam"])}{", " + E(ctx["plaats"]) if ctx["plaats"] else ""}</p></div></div></div>'


def fris_diensten(ctx):
    chips = "".join(f"<li>{E(n)}</li>" for n, _, _ in ctx["diensten"][:8])
    arts = "".join(f"<article><h3>{E(n)}</h3><p>{E(o)}</p></article>" for n, o, _ in ctx["diensten"][:4])
    return f'<section><div class="wrap"><h2>Hier helpen we mee</h2><ul class="chips">{chips}</ul><div class="diensten-c">{arts}</div><p style="margin-top:1.6rem"><a class="pijl" href="diensten">Bekijk alle diensten →</a></p></div></section>'


def fris_over(ctx):
    tekst = E(ctx["intro_lang"] or ctx["t"]["sub"]) if not ctx["intro_lang"] else E(ctx["t"]["sub"])
    return f'<section class="over-c"><div class="wrap"><div><h2>{E(ctx["naam"])}{" in " + E(ctx["plaats"]) if ctx["plaats"] else ""}</h2><p class="intro">{tekst}</p></div><div>{_feiten(ctx)}</div></div></section>'


def fris_galerij(ctx):
    g = ctx["galerij"]
    if len(g) < 4:
        return ""
    return f'<section><div class="wrap"><div class="galerij-c">{"".join(_foto(x) for x in g[:8])}</div></div></section>'


def fris_slot(ctx):
    return f'<section><div class="wrap"><div class="slot-c"><div><h2>{E(ctx["t"]["cta"][0])}</h2><p>{E(ctx["t"]["cta"][1])}</p></div><div class="acties"><a class="knop" href="contact">Neem contact op</a>{_tel_link(ctx)}</div></div></div></section>'


# ====================================================================================
# STIJL D — editorial: grote serif-kop, hairlines, foto onder de tekst, sober
# ====================================================================================
EDITORIAL_CSS = """
:root{--kopfont:'Playfair Display',Georgia,serif;--tekstfont:'Source Sans 3',system-ui,sans-serif;--kopgewicht:600;--kopspatie:-.01em;--knopr:0;--r:0;--h1:clamp(2.4rem,6vw,4.6rem);--h2:clamp(1.6rem,3vw,2.3rem);--max:1080px}
body{line-height:1.65}
header.top{border-top:1px solid var(--ink);border-bottom:1px solid var(--ink)}
header.top>.wrap{padding-top:1rem;padding-bottom:1rem}
.merk b{font-size:1.5rem;font-weight:600}
nav.hoofd a{font-size:.95rem;letter-spacing:.02em}nav.hoofd .tel{font-family:var(--kopfont);font-size:1.05rem}
.knop{background:var(--ink);border-color:var(--ink);letter-spacing:.04em}.knop:hover{background:var(--accent);border-color:var(--accent)}
.hero-d{padding:clamp(3rem,7vw,6rem) 0 clamp(2rem,4vw,3rem)}
.hero-d h1{max-width:16ch;margin-bottom:.5em}
.hero-d .rij{display:grid;gap:2rem;grid-template-columns:2fr 1fr;align-items:end;border-top:1px solid var(--ink);padding-top:1.4rem}
@media (max-width:700px){.hero-d .rij{grid-template-columns:1fr}}
.hero-d .intro{font-size:1.15rem;margin:0}
.hero-d .zij{font-size:.95rem;color:var(--zacht)}.hero-d .zij b{color:var(--ink);display:block}
.beeld-d{padding:0 0 clamp(2rem,5vw,4rem)}.beeld-d img{width:100%;aspect-ratio:21/9;object-fit:cover}
.beeld-d figcaption{font-size:.85rem;color:var(--zacht);padding-top:.6rem;border-bottom:1px solid var(--rand);padding-bottom:.6rem}
.diensten-d{max-width:66ch}.diensten-d article{border-top:1px solid var(--rand);padding:1.2rem 0}
.diensten-d article:last-child{border-bottom:1px solid var(--rand)}
.diensten-d h3{font-size:1.45rem;margin-bottom:.2rem}.diensten-d p{margin:0;color:var(--zacht)}
.over-d .wrap{display:grid;gap:3rem;grid-template-columns:3fr 2fr;align-items:start}
@media (max-width:700px){.over-d .wrap{grid-template-columns:1fr}}
.over-d{border-top:1px solid var(--ink)}
.over-d .intro{font-size:1.2rem}
.over-d .feiten{border-top:1px solid var(--rand);padding-top:1rem}
.galerij-d{display:grid;gap:1rem;grid-template-columns:2fr 1fr}.galerij-d img{width:100%;height:100%;object-fit:cover;aspect-ratio:4/3}
@media (max-width:640px){.galerij-d{grid-template-columns:1fr}}
.slot-d{border-top:1px solid var(--ink);text-align:center}
.slot-d .groot{font-family:var(--kopfont);font-size:clamp(2rem,5vw,3.4rem);font-weight:600;margin:.2em 0 .6em}.slot-d .groot a{color:var(--ink);text-decoration:none}.slot-d .groot a:hover{color:var(--accent)}
footer.onder{--voetbg:var(--papier);--voettekst:var(--ink);border-top:1px solid var(--ink)}footer.onder a,footer.onder h2{color:var(--ink)}.klein{border-top-color:var(--rand)}
"""
EDITORIAL_PALETTEN = [
    dict(accent="#1f4d2b", papier="#ffffff", ink="#111411", zacht="#555a55", rand="#d9dbd7", vel="#f3f4f1"),
    dict(accent="#6b1f2a", papier="#fffefc", ink="#161213", zacht="#5b5455", rand="#dcd8d6", vel="#f5f2f0"),
    dict(accent="#1b2a49", papier="#ffffff", ink="#101318", zacht="#525663", rand="#d7d9df", vel="#f1f2f5"),
    dict(accent="#7a4d0e", papier="#fffdf8", ink="#171410", zacht="#5c564d", rand="#dfdad0", vel="#f6f2ea"),
]


def editorial_hero(ctx):
    intro = ctx["intro_kort"]
    h1 = intro if intro and 30 < len(intro) <= 90 else ctx["naam"]
    if h1 != ctx["naam"]:
        rest = ctx["intro_rest"]
        onder = rest if rest and len(rest) > 40 else ctx["t"]["sub"]
    else:
        onder = ctx["sub"]
    zij = []
    if ctx["plaats"]:
        zij.append(f'<b>{E(ctx["branche_woord"].capitalize() if ctx["branche_woord"] else "Gevestigd")} in {E(ctx["plaats"])}</b>')
    if ctx["tel"]:
        zij.append(f'<a href="tel:{E(ctx["tel"])}" style="color:var(--ink)">{E(ctx["tel_mooi"])}</a>')
    zij.append(f'<a class="pijl" href="contact">{E(ctx["t"]["knop"])}</a>')
    return f'<div class="hero-d"><div class="wrap"><h1>{E(h1)}</h1><div class="rij"><p class="intro">{E(onder)}</p><p class="zij">{"<br>".join(zij)}</p></div></div></div>'


def editorial_beeld(ctx):
    if not ctx["hero"]:
        return ""
    cap = E(ctx["naam"]) + (", " + E(ctx["plaats"]) if ctx["plaats"] else "")
    return f'<div class="beeld-d"><div class="wrap"><figure style="margin:0">{_foto(ctx["hero"], lazy=False)}<figcaption>{cap}</figcaption></figure></div></div>'


def editorial_diensten(ctx):
    arts = "".join(f"<article><h3>{E(n)}</h3><p>{E(o)}</p></article>" for n, o, _ in ctx["diensten"][:6])
    return f'<section><div class="wrap"><p class="eyebrow">Diensten</p><div class="diensten-d">{arts}</div><p style="margin-top:1.4rem"><a class="pijl" href="diensten">Meer over onze diensten →</a></p></div></section>'


def editorial_over(ctx):
    return f'<section class="over-d"><div class="wrap"><div><p class="eyebrow">Over {E(ctx["naam"])}</p><p class="intro">{E(ctx["intro_lang"] or ctx["t"]["sub"])}</p></div><div>{_feiten(ctx)}</div></div></section>'


def editorial_galerij(ctx):
    g = [x for x in ctx["galerij"] if not ctx["hero"] or x["bestand"] != ctx["hero"]["bestand"]]
    if len(g) < 2:
        return ""
    return f'<section style="padding-top:0"><div class="wrap"><div class="galerij-d">{_foto(g[0])}{_foto(g[1])}</div></div></section>'


def editorial_slot(ctx):
    tel = f'<p class="groot"><a href="tel:{E(ctx["tel"])}">{E(ctx["tel_mooi"])}</a></p>' if ctx["tel"] else ""
    return f'<section class="slot-d"><div class="wrap"><p class="eyebrow">{E(ctx["t"]["cta"][0])}</p>{tel}<p><a class="knop" href="contact">{E(ctx["t"]["knop"])}</a></p></div></section>'


# ====================================================================================
# STIJL E — strak: licht grijs, witte kaarten, dienstrijen met pijl, scrollende fotostrook
# ====================================================================================
STRAK_CSS = """
:root{--kopfont:'Manrope',system-ui,sans-serif;--tekstfont:'Manrope',system-ui,sans-serif;--kopgewicht:800;--kopspatie:-.03em;--knopr:10px;--r:12px;--h1:clamp(2.3rem,5.4vw,4rem);--kaartbg:#fff}
header.top{position:sticky;top:0;z-index:20;background:rgba(255,255,255,.92);backdrop-filter:blur(8px)}
nav.hoofd a{font-weight:600;font-size:.95rem}
.hero-e{padding:clamp(2rem,5vw,4rem) 0}
.hero-e .wrap{display:grid;gap:clamp(1.5rem,4vw,3rem);grid-template-columns:repeat(auto-fit,minmax(min(100%,320px),1fr));align-items:center}
.hero-e h1{max-width:14ch}.hero-e .intro{font-size:1.12rem}
.kaartfoto{background:#fff;padding:.6rem;border-radius:calc(var(--r) + 6px);box-shadow:0 20px 50px -30px rgba(0,0,0,.35)}
.kaartfoto img{border-radius:var(--r);aspect-ratio:4/3;object-fit:cover;width:100%}
.hero-e--vlak .wrap{display:block}.hero-e--vlak h1{max-width:20ch}
.rijen{list-style:none;margin:0;padding:0;background:#fff;border-radius:var(--r);overflow:hidden;border:1px solid var(--rand)}
.rijen li{display:grid;grid-template-columns:auto 1fr auto;gap:1.2rem;align-items:center;padding:1.1rem 1.4rem;border-top:1px solid var(--rand)}
.rijen li:first-child{border-top:0}
.rijen .nr{font-weight:800;color:var(--accent);font-variant-numeric:tabular-nums}
.rijen h3{margin:0 0 .15rem;font-size:1.1rem}.rijen p{margin:0;color:var(--zacht);font-size:.95rem}
.rijen .pijltje{color:var(--accent);font-weight:800;font-size:1.3rem}
.strook-e{display:flex;gap:.8rem;overflow-x:auto;scroll-snap-type:x mandatory;padding:0 clamp(1rem,4vw,2rem) 1rem;scrollbar-width:thin}
.strook-e img{flex:0 0 min(78vw,360px);aspect-ratio:4/3;object-fit:cover;border-radius:var(--r);scroll-snap-align:start}
.over-e .wrap{display:grid;gap:1.5rem;grid-template-columns:repeat(auto-fit,minmax(min(100%,300px),1fr))}
.over-e .kaart{padding:2rem}.over-e .intro{margin:0}
.slot-e{background:var(--ink);color:#fff;border-radius:var(--r);padding:clamp(2rem,5vw,3.5rem);display:flex;gap:2rem;flex-wrap:wrap;align-items:center;justify-content:space-between}
.slot-e h2{color:#fff;margin-bottom:.2rem}.slot-e p{margin:0;color:#d9dcd6}
.slot-e .knop{background:#fff;color:var(--ink);border-color:#fff}.slot-e .knop:hover{background:var(--vel);border-color:var(--vel)}
footer.onder{--voetbg:var(--papier);--voettekst:var(--ink);border-top:1px solid var(--rand)}footer.onder a,footer.onder h2{color:var(--ink)}.klein{border-top-color:var(--rand)}
"""
STRAK_PALETTEN = [
    dict(accent="#2f4fd8", papier="#f4f5f7", ink="#15181d", zacht="#565b66", rand="#e1e3e8", vel="#e9ebef"),
    dict(accent="#1d7a4f", papier="#f4f6f4", ink="#141a16", zacht="#525b55", rand="#dfe4e0", vel="#e7ece8"),
    dict(accent="#c4501c", papier="#f7f5f2", ink="#1b1815", zacht="#5b564f", rand="#e5e0da", vel="#ede8e2"),
    dict(accent="#1f6f8b", papier="#f3f6f7", ink="#141b1e", zacht="#515c61", rand="#dde4e7", vel="#e6edf0"),
]


def strak_hero(ctx):
    acties = f'<div class="acties"><a class="knop" href="contact">{E(ctx["t"]["knop"])}</a>{_tel_link(ctx)}</div>'
    tekst = f'<div><p class="eyebrow">{E(ctx["branche_woord"].capitalize() if ctx["branche_woord"] else "")}{" · " + E(ctx["plaats"]) if ctx["plaats"] else ""}</p><h1>{E(ctx["naam"])}</h1><p class="intro">{E(ctx["sub"])}</p>{acties}</div>'
    if ctx["hero"]:
        return f'<div class="hero-e"><div class="wrap">{tekst}<div class="kaartfoto">{_foto(ctx["hero"], lazy=False)}</div></div></div>'
    return f'<div class="hero-e hero-e--vlak"><div class="wrap">{tekst}</div></div>'


def strak_diensten(ctx):
    li = "".join(f'<li><span class="nr">{i:02d}</span><div><h3>{E(n)}</h3><p>{E(o)}</p></div><span class="pijltje" aria-hidden="true">→</span></li>' for i, (n, o, _) in enumerate(ctx["diensten"][:6], 1))
    return f'<section><div class="wrap"><h2>Diensten</h2><ul class="rijen">{li}</ul><p style="margin-top:1.4rem"><a class="pijl" href="diensten">Alle diensten →</a></p></div></section>'


def strak_strook(ctx):
    g = ctx["galerij"]
    if len(g) < 3:
        return ""
    return f'<section style="padding-top:0"><div class="strook-e" tabindex="0" role="region" aria-label="Foto\'s">{"".join(_foto(x) for x in g[:8])}</div></section>'


def strak_over(ctx):
    return f'<section class="over-e"><div class="wrap"><div class="kaart"><h2>{E(ctx["naam"])}</h2><p class="intro">{E(ctx["intro_lang"] or ctx["t"]["sub"])}</p></div><div class="kaart"><h2 style="font-size:1.1rem">Contact</h2>{_feiten(ctx)}</div></div></section>'


def strak_slot(ctx):
    return f'<section style="padding-top:0"><div class="wrap"><div class="slot-e"><div><h2>{E(ctx["t"]["cta"][0])}</h2><p>{E(ctx["t"]["cta"][1])}</p></div><a class="knop" href="contact">Neem contact op</a></div></div></section>'


# ====================================================================================
STIJLEN = {
    "klassiek": dict(fonts=["fraunces", "worksans"], css=KLASSIEK_CSS, paletten=KLASSIEK_PALETTEN, tel_als_knop=False,
                     volgorde=[klassiek_hero, klassiek_diensten, klassiek_over, _werk, klassiek_galerij, klassiek_slot]),
    "robuust": dict(fonts=["barlowcondensed", "barlow"], css=ROBUUST_CSS, paletten=ROBUUST_PALETTEN, tel_als_knop=True,
                    volgorde=[robuust_hero, robuust_strook, robuust_diensten, robuust_over, _werk, robuust_galerij, robuust_slot]),
    "fris": dict(fonts=["nunito"], css=FRIS_CSS, paletten=FRIS_PALETTEN, tel_als_knop=True,
                 volgorde=[fris_hero, fris_quote, fris_diensten, _werk, fris_galerij, fris_over, fris_slot]),
    "editorial": dict(fonts=["playfair", "sourcesans"], css=EDITORIAL_CSS, paletten=EDITORIAL_PALETTEN, tel_als_knop=False,
                      volgorde=[editorial_hero, editorial_beeld, editorial_diensten, editorial_over, _werk, editorial_galerij, editorial_slot]),
    "strak": dict(fonts=["manrope"], css=STRAK_CSS, paletten=STRAK_PALETTEN, tel_als_knop=True,
                  volgorde=[strak_hero, strak_diensten, strak_strook, strak_over, _werk, strak_slot]),
}


def kies(domein, m, voorkeur=None):
    """Stijlnaam en palet voor dit bedrijf. Voorspelbaar via hash van het domein."""
    h = int(hashlib.md5((domein or "").encode()).hexdigest(), 16)
    if voorkeur in STIJLEN:
        naam = voorkeur
    else:
        fotos = m.get("aantal_foto") or 0
        kandidaten = list(STIJLEN) if fotos >= 3 else ["klassiek", "editorial", "strak"] if fotos else ["klassiek", "editorial"]
        naam = kandidaten[h % len(kandidaten)]
    st = STIJLEN[naam]
    pal = dict(st["paletten"][(h // 7) % len(st["paletten"])])
    if m.get("accent"):
        pal["accent"] = leesbaar_op_wit(m["accent"])
    pal["accent"] = leesbaar_op_wit(pal["accent"])
    pal["tint"] = meng(pal["accent"], "#ffffff", 0.88)
    # accent wordt ook als linkkleur gebruikt op papier, vel en tint: overal ≥ 4.6:1
    for _ in range(10):
        if all(contrast(pal["accent"], bg) >= 4.6 for bg in (pal["papier"], pal["vel"], pal["tint"])):
            break
        pal["accent"] = donker(pal["accent"], 0.1)
        pal["tint"] = meng(pal["accent"], "#ffffff", 0.88)
    pal["accent_d"] = donker(pal["accent"], 0.22)
    # zachte tekstkleur moet op papier, vel én tint nog 4.6:1 halen
    for _ in range(10):
        if all(contrast(pal["zacht"], bg) >= 4.6 for bg in (pal["papier"], pal["vel"], pal["tint"], "#ffffff")):
            break
        pal["zacht"] = donker(pal["zacht"], 0.12)
    return naam, pal


def css_voor(naam, pal):
    st = STIJLEN[naam]
    fontcss = "".join(open(os.path.join(HIER, "vendor", "fonts", f"{f}.css"), encoding="utf-8").read() for f in st["fonts"])
    variabelen = (f":root{{--accent:{pal['accent']};--accent-d:{pal['accent_d']};--papier:{pal['papier']};--ink:{pal['ink']};"
                  f"--zacht:{pal['zacht']};--rand:{pal['rand']};--vel:{pal['vel']};--tint:{pal['tint']}}}")
    return fontcss + BASIS + variabelen + st["css"]


def fontbestanden(naam):
    st = STIJLEN[naam]
    uit = []
    for f in st["fonts"]:
        css = open(os.path.join(HIER, "vendor", "fonts", f"{f}.css"), encoding="utf-8").read()
        uit += re.findall(r"url\(fonts/([^)]+)\)", css)
    return uit
