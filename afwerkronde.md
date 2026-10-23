# Afwerkronde — Gmail-concepten klaarmaken om te versturen

Getest op 23-10-2026 met 7 echte concepten (kappers) en één testconcept.

## Waarom deze ronde nodig is

De Gmail-koppeling (create_draft / update_draft) schrijft **elke** link om naar
`https://www.google.com/url?q=…&source=gmail&ust=…`, ook in de platte tekst. Wie daarop klikt,
krijgt eerst een Google-pagina "Redirect Notice". Dat oogt als phishing. Afbeeldingen kan de
koppeling niet plaatsen: een `<img>` met een adres wordt eruit gehaald, en een inline bijlage
vergt duizenden tekens base64 per mail.

Wat wél werkt: het concept openen in Gmail in de browser (Claude in Chrome), daar de links
terugzetten en de schermafbeelding plakken. Gmail slaat dat zelf op, met schone links en de
afbeelding als inline bijlage (`cid:`), die ook in Outlook direct zichtbaar is.

**Daarna nooit meer update_draft op dat concept doen** — dan schrijft de koppeling de links weer om
en verdwijnt de afbeelding.

## Stappen

1. Schermafbeeldingen maken (in de cloudsessie):
   `python3 schermafbeelding.py <scratchpad> <slug> …` → `<scratchpad>/voorbeeld-<slug>.jpg`.
   De scratchpad is belangrijk: Claude in Chrome kan alleen bestanden uploaden die met de sessie
   gedeeld zijn.
2. In Chrome: Gmail openen op `#drafts` en **de pagina herladen** (F5). Een Gmail-tabblad dat al open
   stond, kent nog de oude versie van een concept; sluiten zonder herladen zet die oude versie terug
   (gebeurd op 23-10 bij Kapsalon New Look).
3. Eén keer per pagina de hulpfuncties hieronder laden (javascript_tool).
4. Per concept:
   - rij openen (find "draft list row with subject containing '<naam>'" → klik);
   - `tdsPrep('<slug>')` → zet links terug, vervangt de plek-regel door een merkteken en maakt een
     verborgen bestandsveld "TDS upload";
   - `find "file input labelled 'TDS upload'"` → `file_upload` met `voorbeeld-<slug>.jpg`;
   - `tdsPaste()` → plakt de afbeelding op de plek (Gmail uploadt hem als inline afbeelding);
   - na ±3 s `tdsFinish('Voorbeeld van de nieuwe homepage van <bedrijf>')` → zet breedte 560 en de
     juiste hoogte, cursor naar het eind;
   - een echte toetsaanslag (spatie, dan Backspace) zodat Gmail opslaat; wachten tot
     "Concept opgeslagen"; venster sluiten.
5. Controleren met get_draft: `<img … src="cid:…" width="560" height="350">`, geen `google.com/url`,
   geen `[[AFBEELDING`.

## Hulpfuncties (javascript_tool)

```js
window.tdsBodyVoor = s => Array.from(document.querySelectorAll('div[contenteditable="true"][role="textbox"]')).find(x => x.innerHTML.includes(s));
window.tdsSchoon = function (b) {
  let n = 0;
  b.querySelectorAll('a[href]').forEach(a => {
    const h = a.getAttribute('href');
    if (h.startsWith('https://www.google.com/url?')) {
      const q = new URL(h).searchParams.get('q');
      if (q) { a.setAttribute('href', q); a.removeAttribute('data-saferedirecturl'); if (a.textContent.includes('google.com/url')) a.textContent = q.replace(/^https?:\/\//, '').replace(/\/$/, ''); n++; }
    }
  });
  // omgeschreven links die als losse tekst in het concept staan (platte-tekstconcepten)
  const w = document.createTreeWalker(b, NodeFilter.SHOW_TEXT), los = [];
  let t; while ((t = w.nextNode())) if (t.nodeValue.includes('https://www.google.com/url?')) los.push(t);
  los.forEach(t => {
    const frag = document.createDocumentFragment();
    t.nodeValue.split(/(https:\/\/www\.google\.com\/url\?\S+)/).forEach(stuk => {
      const m = stuk.match(/^https:\/\/www\.google\.com\/url\?\S+/);
      if (!m) { frag.appendChild(document.createTextNode(stuk)); return; }
      const q = new URL(stuk).searchParams.get('q');
      const a = document.createElement('a'); a.href = q; a.textContent = q.replace(/^https?:\/\//, '').replace(/\/$/, '');
      frag.appendChild(a); n++;
    });
    t.parentNode.replaceChild(frag, t);
  });
  return n;
};
window.tdsPrep = function (slug) {
  const b = window.tdsBodyVoor(slug + '.tdswebstudio.nl') || window.tdsBodyVoor(slug + '.voorbeelden.pages.dev');
  if (!b) return 'geen concept open voor ' + slug;
  const fixed = window.tdsSchoon(b);
  const w = document.createTreeWalker(b, NodeFilter.SHOW_TEXT); let t, placed = false;
  while ((t = w.nextNode())) {
    const i = t.nodeValue.indexOf('[[AFBEELDING');
    if (i >= 0) {
      const j = t.nodeValue.indexOf(']]', i) + 2;
      const na = t.splitText(i); na.splitText(j - i);
      const sp = document.createElement('span'); sp.id = 'tds-plek'; sp.textContent = 'x';
      na.parentNode.replaceChild(sp, na); placed = true; break;
    }
  }
  const oud = document.getElementById('tds-up'); if (oud) oud.remove();
  const inp = document.createElement('input'); inp.type = 'file'; inp.id = 'tds-up'; inp.accept = 'image/*';
  inp.setAttribute('aria-label', 'TDS upload'); Object.assign(inp.style, { position: 'fixed', top: '5px', left: '400px', zIndex: 99999 });
  document.body.appendChild(inp); window.tdsBody = b;
  return { fixed, placed, links: Array.from(b.querySelectorAll('a')).map(a => a.getAttribute('href')) };
};
window.tdsPaste = function () {
  const f = document.getElementById('tds-up').files[0], b = window.tdsBody, sp = document.getElementById('tds-plek');
  if (!f || !sp) return 'mist bestand of plek';
  b.focus(); const r = document.createRange(); r.selectNodeContents(sp);
  const s = window.getSelection(); s.removeAllRanges(); s.addRange(r);
  const dt = new DataTransfer(); dt.items.add(f);
  b.dispatchEvent(new ClipboardEvent('paste', { clipboardData: dt, bubbles: true, cancelable: true }));
  return 'geplakt ' + f.name;
};
window.tdsFinish = function (alt) {
  const b = window.tdsBody, imgs = b.querySelectorAll('img');
  if (imgs.length !== 1) return 'aantal afbeeldingen: ' + imgs.length;
  const img = imgs[0], nw = img.naturalWidth || 720, nh = img.naturalHeight || 450;
  img.setAttribute('width', '560'); img.setAttribute('height', String(Math.round(560 * nh / nw)));
  img.alt = alt; img.style.maxWidth = '100%';
  const inp = document.getElementById('tds-up'); if (inp) inp.remove();
  b.focus(); const r = document.createRange(); r.selectNodeContents(b); r.collapse(false);
  const s = window.getSelection(); s.removeAllRanges(); s.addRange(r);
  return { w: img.getAttribute('width'), h: img.getAttribute('height'), plek: !!document.getElementById('tds-plek') };
};
```

## Wat er buiten Gmail voor nodig is (staat al)

- DNS-record `*.tdswebstudio.nl` (A 192.0.2.1, proxied) en Worker-route `*.tdswebstudio.nl/*` →
  Worker **voorbeeld-proxy**; route `www.tdswebstudio.nl/*` zonder Worker. De Worker toont
  `<slug>.voorbeelden.pages.dev` onder `<slug>.tdswebstudio.nl`; de adresbalk blijft
  tdswebstudio.nl. Niet-bestaande namen geven 404.
