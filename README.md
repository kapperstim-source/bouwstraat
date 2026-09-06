# Bouwstraat — van bestaande website naar demo en verkoopmail

Gereedschap van Tim Kappers om kleine bedrijven met een verouderde website een voorbeeld
van een nieuwe site te sturen. Alles draait op Python 3 (standaardbibliotheek + Pillow +
Playwright) en `npx wrangler` voor het online zetten.

    python3 run.py https://doelsite.nl --branche hoveniers          # één site, lokaal
    python3 run.py https://doelsite.nl --branche hoveniers --deploy # + online op Cloudflare Pages

## Onderdelen

| Script | Doet |
|---|---|
| `oogst.py` | bedrijven met website ophalen uit OpenStreetMap (per branche, heel Nederland) |
| `sitescan.py` | site doorlichten: score 0-100, bevindingen in gewoon Nederlands, e-mail/telefoon/KvK, platform, commercieel belang |
| `extract.py` | site uitlezen → `content.json` (naam, NAW, diensten, projecten, foto's, logo) |
| `images.py` | foto's ophalen, WebP, logo en hero kiezen, accentkleur uit het logo |
| `teksten.py` | voorstel-teksten per branche (over het vak, nooit over het bedrijf) |
| `build.py` | drie pagina's + privacy + 404 + robots.txt, contactformulier, `NALOPEN.md` |
| `stijlen.py` | vijf huisstijlen (klassiek, robuust, fris, editorial, strak): eigen lettertypes, paletten, opbouw; keuze per domein |
| `fonts.py` | haalt de lettertypes (OFL) één keer op naar `vendor/fonts/`; demo's leveren ze zelf mee |
| `verify.py` | Playwright: links, scriptfouten, axe-core, horizontale scroll, screenshots |
| `deploy.py` | online zetten op Cloudflare Pages als branch van één project (`<slug>.voorbeelden.pages.dev`) |
| `mail.py` | verkoopmail uit scan + demo (onderwerp: "Voorbeeld van een nieuwe website voor …") |
| `run.py` | één site van begin tot eind |
| `weekronde.py` | de wekelijkse ronde: kalender → oogst/voorraad → scan → kiezen → bouwen → `concepten.json` |

## Wekelijkse ronde (geplande taak "Prospect-agent websiteverkoop")

    git clone --depth 1 https://github.com/kapperstim-source/bouwstraat
    cd bouwstraat            # config.json (uit Drive) ernaast zetten; deploy.py leest het token daaruit
    python3 weekronde.py --werkmap /tmp/ronde --administratie administratie.json \
        --kalender kalender.json --config config.json --voorraad voorraad --aantal 10 --deploy

Daarna maakt de agent per regel in `/tmp/ronde/concepten.json` een Gmail-concept en zet
`/tmp/ronde/administratie.json` terug in Google Drive (map Websiteverkoop).

Bestanden in Drive (map Websiteverkoop): `administratie.json` (wie is benaderd of
overgeslagen, kalenderstand, afmeldingen), `kalender.json` (volgorde van branches),
`config.json` (Cloudflare-token en -account-id, prijs, maandbedrag), `voorraad/<branche>.json`
(geoogste bedrijven, zodat de weekronde niet van Overpass afhangt). De voorraad staat sinds
05-09 in de repo: 22 branches, 16.009 bedrijven, 4.459 met e-mailadres.

## Regels die in de code zitten

- Geen verzonnen feiten: teksten gaan over het vak; wat feit en wat voorstel is staat in `NALOPEN.md`.
- Elke demo: melding "voorbeeldontwerp" boven- en onderaan, `noindex`, `robots.txt` dicht.
- Over certificaten/https staat niets in de mail (vanuit de cloudomgeving niet te beoordelen).
- Mail alleen naar het adres dat het bedrijf zelf publiceert (bij voorkeur `info@`).
- Afgemelde adressen (`afgemeld` in administratie.json) worden nooit meer benaderd.
- Wix/Squarespace/Shopify/Webflow/JouwWeb-sites zijn geen prospect.

## Omgeving

- TLS loopt via een proxy: certificaatcontrole staat uit in `sitescan.py`; gebruik `curl -k`.
- Overpass: `overpass.kumi.systems` en `overpass.private.coffee`; `overpass-api.de` reset vaak.
  Heel Nederland in één query lukt met het `["website"]`-filter (±40–200 s), maar niet altijd —
  daarom de voorraadbestanden.
- Wrangler via `npx --yes wrangler@4` (±15 s de eerste keer).
