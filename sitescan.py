#!/usr/bin/env python3
"""sitescan.py — licht een website door en geeft een score van 0-100 plus bevindingen
in gewoon Nederlands. Alleen standaardbibliotheek.

    python3 sitescan.py https://voorbeeld.nl            → JSON op stdout
    python3 sitescan.py --lijst sites.txt --uit scans.jsonl [--workers 8]

Let op (zie prospect-pipeline.md): certificaten zijn vanuit de cloudomgeving niet te
beoordelen — alle TLS loopt via een proxy. Daarom wordt certificaatcontrole uitgezet en
zeggen we nooit iets over certificaten in een mail.
"""
import argparse, json, re, ssl, sys, time, html
import urllib.request, urllib.parse, urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
JAAR = date.today().year


def haal(url, timeout=15, max_bytes=2_500_000, method="GET"):
    """Haalt een URL op. Geeft (status, eind_url, bytes, headers, seconden). 403 en andere
    HTTP-fouten leveren tóch de body op (firewalls geven vaak 403 met gewoon de pagina)."""
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "nl,en;q=0.5"}, method=method)
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
            body = r.read(max_bytes) if method == "GET" else b""
            return r.status, r.geturl(), body, dict(r.headers), time.time() - t0
    except urllib.error.HTTPError as e:
        try:
            body = e.read(max_bytes) if method == "GET" else b""
        except Exception:
            body = b""
        return e.code, e.geturl() or url, body, dict(e.headers or {}), time.time() - t0


def decodeer(b, headers):
    ct = (headers.get("Content-Type") or "").lower()
    m = re.search(r"charset=([\w-]+)", ct)
    kandidaten = [m.group(1)] if m else []
    m2 = re.search(rb'charset=["\']?([\w-]+)', b[:4000], re.I)
    if m2:
        kandidaten.append(m2.group(1).decode("ascii", "ignore"))
    kandidaten += ["utf-8", "cp1252", "latin-1"]
    for k in kandidaten:
        try:
            return b.decode(k)
        except Exception:
            continue
    return b.decode("utf-8", "replace")


def normaliseer(url):
    url = url.strip()
    if not re.match(r"^https?://", url, re.I):
        url = "http://" + url
    return url


def host_van(url):
    return urllib.parse.urlsplit(url).netloc.lower().split(":")[0]


def kaal(host):
    return re.sub(r"^www\.", "", host)


CHALLENGE = (r"sgcaptcha|cf-chl|challenge-platform|just a moment|attention required|checking your browser|"
             r"ddos-guard|/cdn-cgi/challenge|verify you are human|bot-protection|captcha-delivery|"
             r"<title>\s*(even geduld|please wait|one moment)")
# jaar van uitgave per jQuery-tak (eerste release van die tak)
JQUERY_JAAR = {(1, 0): 2006, (1, 1): 2007, (1, 2): 2007, (1, 3): 2009, (1, 4): 2010, (1, 5): 2011, (1, 6): 2011, (1, 7): 2011,
               (1, 8): 2012, (1, 9): 2013, (1, 10): 2013, (1, 11): 2014, (1, 12): 2016, (2, 0): 2013, (2, 1): 2014, (2, 2): 2016}
GESTOPT = (r"besloten (om )?(voorlopig |definitief |per [^ ]+ )?te stoppen|(wij |we )?zijn (per [^ ]+ )?gestopt|is (per [^ ]+ )?gestopt met|"
           r"definitief gesloten|voorgoed gesloten|bedrijf is beëindigd|bedrijf is beeindigd|activiteiten (zijn )?(gestaakt|beëindigd)|"
           r"failliet verklaard|faillissement|niet meer open ?gaan|gaan niet meer open|(dit|het) jaar niet meer open|"
           r"wegens beëindiging|bedankt voor (alle|de) jaren|na \d+ jaar (stoppen|gestopt)|we sluiten (de deuren|onze deuren)|sluit (per|op) [^ ]+ (definitief )?de deuren")
GEPARKEERD = (r"yourhosting|domein is gereserveerd|dit domein is geregistreerd|domain is parked|parkeerpagina|"
              r"website in aanbouw|binnenkort online|coming soon|under construction|sedo\.com|"
              r"deze website is nog niet|hostnet\.nl/sitebuilder|strato\.nl/.*domein|mijndomein|"
              r"website wordt gebouwd|nog geen website|op dit moment niet bereikbaar|website is niet bereikbaar")


class Scan:
    def __init__(self, url):
        self.url_in = normaliseer(url)
        self.b = []          # bevindingen: dict(code, punten, zin)
        self.info = {}
        self.score = 0

    def vondst(self, code, punten, zin):
        self.b.append({"code": code, "punten": punten, "zin": zin})

    def run(self):
        info = self.info
        info["url"] = self.url_in
        host = host_van(self.url_in)
        # 1. http → https gedrag
        http_url = "http://" + kaal(host) + "/"
        try:
            st, eind, body, hdr, sec = haal(http_url)
        except Exception as e:
            # http onbereikbaar: probeer https direct
            try:
                st, eind, body, hdr, sec = haal("https://" + kaal(host) + "/")
            except Exception as e2:
                info["fout"] = f"onbereikbaar: {e2.__class__.__name__}: {str(e2)[:120]}"
                return self.resultaat()
        if sec > 3:
            # één keer opnieuw meten: een trage eerste keer is vaak toeval (dns, koude cache)
            try:
                st_b, eind_b, body_b, hdr_b, sec_b = haal(eind, timeout=15)
                if sec_b < sec and body_b:
                    st, eind, body, hdr, sec = st_b, eind_b, body_b, hdr_b, sec_b
            except Exception:
                pass
        info["status"] = st
        info["eind_url"] = eind
        info["laadtijd_s"] = round(sec, 2)
        https_eind = eind.lower().startswith("https://")
        if not https_eind:
            # verwijst niet door; is https wel bereikbaar?  (certificaten zijn hier niet te
            # beoordelen — zie prospect-pipeline.md — dus alleen bereikbaarheid en inhoud)
            try:
                https_host = host_van(eind) if eind else host
                st2, eind2, body2, hdr2, sec2 = haal("https://" + https_host + "/", timeout=15)
                if st2 < 400 and len(body2) > 500 and len(body2) < 60_000 and re.search(GEPARKEERD + "|" + CHALLENGE, decodeer(body2, hdr2).lower()):
                    # https toont een foutpagina van de hoster; de echte site staat alleen op http
                    info["https_bereikbaar"] = "placeholder"
                    self.vondst("https-placeholder", 10, "de beveiligde versie van de site (https) toont een foutpagina van de hostingpartij ('website niet bereikbaar'); wie via Google of een link binnenkomt, kan daar terechtkomen")
                elif st2 < 400 and len(body2) > 500:
                    self.vondst("geen-https-doorverwijzing", 6,
                                "wie het adres zonder https intypt, blijft op de onbeveiligde versie hangen — de browser toont dan 'niet veilig'")
                    info["https_bereikbaar"] = True
                    # gebruik alsnog de https-versie voor de rest
                    st, eind, body, hdr, sec = st2, eind2, body2, hdr2, sec2
                elif st2 < 400:
                    info["https_bereikbaar"] = "leeg"
                    self.vondst("https-leeg", 10, "de beveiligde versie van de site (https) toont een lege pagina; wie via Google binnenkomt kan daar terechtkomen")
                else:
                    info["https_bereikbaar"] = False
                    self.vondst("geen-https", 15, "de site heeft geen werkende beveiligde verbinding (https); de browser zet er 'niet veilig' bij")
            except Exception:
                info["https_bereikbaar"] = False
                self.vondst("geen-https", 15, "de site heeft geen werkende beveiligde verbinding (https); de browser zet er 'niet veilig' bij")
        else:
            info["https_bereikbaar"] = True
        if st >= 400 and len(body) < 500:
            info["fout"] = f"http {st}"
            return self.resultaat()
        if not body:
            info["fout"] = "lege pagina"
            return self.resultaat()

        h = decodeer(body, hdr)
        info["html_kb"] = round(len(body) / 1024)
        laag = h.lower()
        # botbescherming (SiteGround-captcha, Cloudflare-challenge e.d.): we zien niet de echte site,
        # dus niet beoordelen en zeker geen demo van bouwen
        hdr_laag = {str(k).lower(): str(v).lower() for k, v in (hdr or {}).items()} if hasattr(hdr, "items") else {}
        if hdr_laag.get("sg-captcha") or "cf-mitigated" in hdr_laag or re.search(CHALLENGE, laag):
            info["fout"] = "botbescherming: site is vanuit de cloud niet te lezen"
            self.b = []
            return self.resultaat()
        # geparkeerd / in aanbouw: geen echte site, dus geen prospect voor een herbouw
        if len(body) < 60_000 and re.search(GEPARKEERD, laag):
            info["geparkeerd"] = True
            info["fout"] = "geparkeerd of in aanbouw"
            self.b = []
            return self.resultaat()
        tekst = html.unescape(re.sub(r"<[^>]+>", " ", re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", h, flags=re.S | re.I)))
        tekst = re.sub(r"\s+", " ", tekst)
        info["tekst_lengte"] = len(tekst)
        # bedrijf gestopt of (voorlopig) dicht: geen prospect
        if re.search(GESTOPT, tekst.lower()):
            info["gestopt"] = True
            info["fout"] = "bedrijf meldt op de site dat het gestopt of gesloten is"
            self.b = []
            return self.resultaat()
        if len(tekst.strip()) < 40 and "<frame" not in laag and "<iframe" not in laag:
            info["fout"] = "lege pagina: vrijwel geen tekst (doorverwijzing, script-only of afgeschermd)"
            self.b = []
            return self.resultaat()
        basis = eind

        # platform
        platform = None
        for naam, patroon in [("Wix", r"wix\.com|wixstatic|_wixCssModules|wix-"),
                              ("Squarespace", r"squarespace"), ("Shopify", r"cdn\.shopify|shopify"),
                              ("Webflow", r"webflow"), ("JouwWeb", r"jouwweb"), ("Weebly", r"weebly"),
                              ("Jimdo", r"jimdo"), ("Strato Sitebuilder", r"strato.*sitebuilder|sitebuilder.*strato"),
                              ("Hostnet", r"sitebuilder\.hostnet")]:
            if re.search(patroon, laag):
                platform = naam
                break
        info["platform"] = platform
        m = re.search(r'<meta[^>]+name=["\']?generator\b[^>]+content=["\']?([^"\'>]+)', h, re.I)
        if m:
            info["generator"] = m.group(1)[:80]
        if re.search(r"wp-content|wp-includes", laag):
            info["cms"] = "WordPress"
            mv = re.search(r'content=["\']WordPress ([\d.]+)', h, re.I) or re.search(r"wp-includes/[^\"']+\?ver=(\d+\.\d+(?:\.\d+)?)", h)
            if mv:
                v = mv.group(1)
                info["wordpress_versie"] = v
                try:
                    maj = int(v.split(".")[0])
                    if maj < 6:
                        self.vondst("wordpress-oud", 8, f"de site draait op WordPress {v}, een versie van jaren geleden; de huidige tak is 7")
                except ValueError:
                    pass
        elif re.search(r"joomla", laag):
            info["cms"] = "Joomla"
        elif re.search(r"drupal", laag):
            info["cms"] = "Drupal"

        # viewport
        if not re.search(r'<meta[^>]+name=["\']?viewport\b', h, re.I):
            self.vondst("geen-viewport", 25, "op een telefoon wordt de hele site verkleind weergegeven: knijpen en schuiven om iets te lezen — en het meeste bezoek komt via de telefoon")
        # mixed content
        if https_eind and re.search(r'(src|href)=["\']http://(?!' + re.escape(kaal(host)) + r')', h, re.I) and re.search(r'<(img|script|link)[^>]+(src|href)=["\']http://', h, re.I):
            self.vondst("mixed-content", 6, "een deel van de plaatjes of scripts wordt onbeveiligd geladen, waardoor browsers een waarschuwing tonen of onderdelen blokkeren")
        # flash
        if re.search(r"\.swf|shockwave-flash|application/x-shockwave", laag):
            self.vondst("flash", 10, "de site gebruikt Flash, dat sinds 2021 in geen enkele browser meer werkt — dat deel is dus voor niemand zichtbaar")
        # oude tags
        oud = re.findall(r"<(font|center|marquee|frameset|blink)\b", laag)
        if oud:
            self.vondst("oude-html", 8, "de pagina is gebouwd met opmaaktechniek uit de jaren 2000 (<font>-tags); browsers tonen dat steeds slordiger")
        # tabel-layout
        tabellen = len(re.findall(r"<table\b", laag))
        if tabellen >= 3 and not re.search(r"<(article|section|nav|main)\b", laag):
            self.vondst("tabel-layout", 8, "de pagina-indeling is met tabellen gemaakt, wat op een telefoon niet meeschaalt")
        # jquery
        mj = re.search(r"jquery[-.](\d+)\.(\d+)(?:\.(\d+))?(?:\.min)?\.js", laag) or re.search(r"jquery/(\d+)\.(\d+)\.(\d+)", laag)
        if mj:
            maj, mnr = int(mj.group(1)), int(mj.group(2))
            info["jquery_versie"] = f"{maj}.{mnr}" + (f".{mj.group(3)}" if mj.group(3) else "")
            if maj < 3:
                jaar = JQUERY_JAAR.get((maj, mnr), 2006 + maj * 4 + (mnr // 3))
                self.vondst("jquery-oud", 6, f"er wordt een scriptbibliotheek uit {jaar} gebruikt (jQuery {info['jquery_versie']}) met bekende, allang opgeloste problemen")
        mb = re.search(r"bootstrap[-.](\d)\.(\d)", laag)
        if mb:
            info["bootstrap"] = f"{mb.group(1)}.{mb.group(2)}"
            if int(mb.group(1)) <= 3:
                self.vondst("bootstrap-oud", 4, "het opmaakraamwerk (Bootstrap 3 of ouder) wordt niet meer onderhouden")
        if re.search(r"fonts\.googleapis\.com", laag):
            info["google_fonts"] = True
        # laadtijd
        if sec > 6:
            self.vondst("traag", 12, f"de homepage deed er {sec:.1f} seconden over om binnen te komen; na 3 seconden haakt een groot deel van de bezoekers af".replace(".", ","))
        elif sec > 3:
            self.vondst("traag", 8, f"de homepage deed er {sec:.1f} seconden over om binnen te komen; na 3 seconden haakt een groot deel van de bezoekers af".replace(".", ","))
        if len(body) > 300_000:
            self.vondst("html-groot", 4, f"alleen al de pagina-code is {len(body)//1024} kB, ruim meer dan nodig")
        # beelden
        imgs = re.findall(r"<img\b[^>]*>", h, re.I)
        srcs = []
        for tag in imgs:
            ms = re.search(r'\ssrc=["\']?([^"\'\s>]+)', tag, re.I) or re.search(r'\sdata-src=["\']?([^"\'\s>]+)', tag, re.I)
            if ms and not ms.group(1).startswith("data:"):
                srcs.append(urllib.parse.urljoin(basis, ms.group(1)))
        info["aantal_beelden"] = len(imgs)
        zonder_alt = sum(1 for t in imgs if not re.search(r'\salt=(["\'][^"\']+["\']|[^"\'\s>]+)', t, re.I))
        if imgs and zonder_alt / len(imgs) > 0.5:
            self.vondst("alt-ontbreekt", 5, f"{zonder_alt} van de {len(imgs)} foto's hebben geen omschrijving; Google en voorleessoftware weten dan niet wat erop staat")
        if imgs and not re.search(r'loading=["\']?lazy', h, re.I):
            self.vondst("geen-lazy", 3, "alle foto's laden direct, ook die onderaan de pagina waar de bezoeker nog niet is")
        webp = any(re.search(r"\.(webp|avif)(\?|$)", s, re.I) for s in srcs) or "image/webp" in laag
        gewicht = 0
        uniek = list(dict.fromkeys(srcs))[:30]
        if uniek:
            def kop(u):
                try:
                    st_, e_, b_, hd_, s_ = haal(u, timeout=8, method="HEAD")
                    return int(hd_.get("Content-Length") or 0)
                except Exception:
                    return 0
            with ThreadPoolExecutor(max_workers=8) as ex:
                for g in ex.map(kop, uniek):
                    gewicht += g
        info["beeld_mb"] = round(gewicht / 1e6, 2)
        if gewicht > 3e6:
            self.vondst("beeld-zwaar", 8, f"de foto's op de homepage wegen samen {gewicht/1e6:.1f} MB; op mobiel internet is dat lang wachten en veel databundel".replace(".", ","))
        if uniek and not webp:
            self.vondst("geen-webp", 3, "de foto's staan in een verouderd bestandsformaat; hetzelfde beeld kan 60 tot 80 procent kleiner")
        # seo-basis
        mt = re.search(r"<title[^>]*>(.*?)</title>", h, re.I | re.S)
        titel = html.unescape(mt.group(1)).strip() if mt else ""
        info["titel"] = titel[:120]
        if not titel:
            self.vondst("geen-title", 5, "de pagina heeft geen titel; in Google en in het browsertabblad staat dan alleen het webadres")
        if not re.search(r'<meta[^>]+name=["\']?description\b[^>]+content=["\']?[^"\'>]{20,}', h, re.I) and not re.search(r'<meta[^>]+content=["\']?[^"\'>]{20,}[^>]+name=["\']?description\b', h, re.I):
            self.vondst("geen-description", 5, "er is geen omschrijving voor Google ingesteld, dus Google kiest zelf een willekeurig stukje tekst als samenvatting")
        if not re.search(r"<h1\b", laag):
            self.vondst("geen-h1", 4, "de pagina heeft geen hoofdkop, wat het voor Google lastiger maakt om te zien waar de site over gaat")
        if not re.search(r'<link[^>]+rel=["\']?canonical', h, re.I):
            self.vondst("geen-canonical", 2, "er is niet aangegeven welk adres het hoofdadres is (met en zonder www), waardoor Google de site dubbel kan zien")
        if not re.search(r'property=["\']?og:', h, re.I):
            self.vondst("geen-og", 3, "wie de site deelt via WhatsApp of Facebook krijgt geen voorvertoning met foto en titel")
        if not re.search(r"schema\.org|application/ld\+json", laag):
            self.vondst("geen-schema", 3, "bedrijfsgegevens zijn niet in de code gemarkeerd, waardoor Google openingstijden en adres niet direct kan tonen")
        # copyright
        jaren = [int(j) for j in re.findall(r"(?:©|&copy;|copyright)\s*(?:\d{4}\s*[-–]\s*)?((?:19|20)\d{2})", h, re.I)]
        if jaren:
            j = max(jaren)
            info["copyright_jaar"] = j
            if j <= JAAR - 3:
                self.vondst("copyright-oud", 6, f"onderaan de site staat nog '© {j}'; een bezoeker leest dat als 'hier is al jaren niets aan gedaan'")
        # analytics / cookies
        analytics = bool(re.search(r"google-analytics\.com|googletagmanager\.com/gtag|gtag\(|_gaq|analytics\.js", laag))
        info["analytics"] = analytics
        cookie = bool(re.search(r"cookie(consent|banner|melding|wall|bar|notice|bot)|cookiebot|complianz|cookieyes|gdpr", laag))
        if analytics and not cookie:
            self.vondst("analytics-zonder-cookiemelding", 4, "de site meet bezoekers met Google Analytics maar vraagt daar geen toestemming voor, wat volgens de AVG wel moet")
        if not re.search(r"privacy|privacyverklaring|privacybeleid", laag):
            self.vondst("geen-privacy", 3, "er staat geen privacyverklaring op de site, terwijl die verplicht is zodra er een contactformulier is")
        # commercieel belang
        belang = []
        if re.search(r"googleads|googleadservices|gtag\(['\"]config['\"],\s*['\"]AW-|conversion_async|adsbygoogle", laag):
            belang.append("Google Ads")
        if re.search(r"fbq\(|connect\.facebook\.net/[^/]+/fbevents", laag):
            belang.append("Meta-pixel")
        if re.search(r"woocommerce|add-to-cart|winkelwagen|/cart\b|shopify", laag):
            belang.append("webshop")
        if re.search(r"klantenvertellen|trustpilot|kiyoh|feedbackcompany|google reviews|reviews\.io|werkspot", laag):
            belang.append("reviews")
        if re.search(r"tawk\.to|crisp\.chat|livechat|whatsapp.*widget|wa\.me/|api\.whatsapp\.com", laag):
            belang.append("chat/WhatsApp")
        if re.search(r"offerte", laag):
            belang.append("offerteknop")
        info["belang"] = belang
        # gegevens
        mails = set(m.lower() for m in re.findall(r"[\w.+-]+@[\w-]+\.[\w.-]+", html.unescape(h)))
        mails = {m.rstrip(".") for m in mails if not re.search(r"\.(png|jpg|jpeg|gif|svg|webp|css|js)$", m) and "example" not in m and "sentry" not in m and "wixpress" not in m}
        mm = re.findall(r'mailto:([^"\'?]+)', h, re.I)
        mails |= {m.lower() for m in mm}
        tels = set()
        for t in re.findall(r"(?:\+31|0031|0)[\s-]?(?:\d[\s-]?){8,9}\d", tekst):
            cijfers = re.sub(r"\D", "", t)
            if cijfers.startswith("31"):
                cijfers = "0" + cijfers[2:]
            if len(cijfers) == 10 and cijfers.startswith("0"):
                tels.add(cijfers)
        mk = re.search(r"(?:kvk|k\.v\.k\.|kamer van koophandel)[^\d]{0,25}(\d{8})", tekst, re.I)
        if not mails or not tels:
            for pad in ("/contact", "/contact/", "/over-ons", "/contact.html", "/contact.php"):
                try:
                    st3, e3, b3, h3, s3 = haal(urllib.parse.urljoin(basis, pad), timeout=10)
                    if st3 < 400 and b3:
                        h3t = decodeer(b3, h3)
                        for m in re.findall(r"[\w.+-]+@[\w-]+\.[\w.-]+", html.unescape(h3t)):
                            m = m.lower().rstrip(".")
                            if not re.search(r"\.(png|jpg|jpeg|gif|svg|webp|css|js)$", m):
                                mails.add(m)
                        mails |= {m.lower() for m in re.findall(r'mailto:([^"\'?]+)', h3t, re.I)}
                        t3 = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", h3t)))
                        for t in re.findall(r"(?:\+31|0031|0)[\s-]?(?:\d[\s-]?){8,9}\d", t3):
                            cijfers = re.sub(r"\D", "", t)
                            if cijfers.startswith("31"):
                                cijfers = "0" + cijfers[2:]
                            if len(cijfers) == 10 and cijfers.startswith("0"):
                                tels.add(cijfers)
                        if not mk:
                            mk = re.search(r"(?:kvk|k\.v\.k\.|kamer van koophandel)[^\d]{0,25}(\d{8})", t3, re.I)
                        if mails and tels:
                            break
                except Exception:
                    continue
        eigen = [m for m in mails if kaal(host).split(".")[0] in m]
        voorkeur = sorted(mails, key=lambda m: (0 if kaal(host) in m else 1, 0 if m.startswith("info@") else 1, m))
        info["emails"] = voorkeur[:5]
        info["email"] = voorkeur[0] if voorkeur else None
        info["telefoon"] = sorted(tels)[:3]
        info["kvk"] = mk.group(1) if mk else None
        return self.resultaat()

    def resultaat(self):
        score = min(100, sum(b["punten"] for b in self.b))
        self.score = score
        if self.info.get("geparkeerd"):
            klasse = "geparkeerd"
        elif self.info.get("fout"):
            klasse = "onbereikbaar"
        elif score >= 55:
            klasse = "heet"
        elif score >= 30:
            klasse = "warm"
        elif score >= 15:
            klasse = "lauw"
        else:
            klasse = "prima"
        self.b.sort(key=lambda x: -x["punten"])
        return {"url": self.url_in, "score": score, "klasse": klasse, "platform_vast": bool(self.info.get("platform")),
                "bevindingen": self.b, **self.info}


def scan(url):
    try:
        return Scan(url).run()
    except Exception as e:
        return {"url": url, "score": 0, "klasse": "onbereikbaar", "bevindingen": [], "fout": f"{e.__class__.__name__}: {str(e)[:150]}"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("url", nargs="?")
    ap.add_argument("--lijst", help="tekstbestand met één url per regel")
    ap.add_argument("--uit", help="jsonl-bestand voor de uitkomsten")
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args()
    if a.url:
        print(json.dumps(scan(a.url), ensure_ascii=False, indent=2))
        return
    urls = [r.strip() for r in open(a.lijst, encoding="utf-8") if r.strip() and not r.startswith("#")]
    uit = open(a.uit, "a", encoding="utf-8") if a.uit else sys.stdout
    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        futs = {ex.submit(scan, u): u for u in urls}
        for i, f in enumerate(as_completed(futs), 1):
            r = f.result()
            uit.write(json.dumps(r, ensure_ascii=False) + "\n")
            uit.flush()
            print(f"[{i}/{len(urls)}] {r.get('score'):>3} {r.get('klasse'):<12} {r['url']}", file=sys.stderr)


if __name__ == "__main__":
    main()
