#!/usr/bin/env python3
"""schermafbeelding.py — maakt per demo een schermafbeelding van de homepage voor in de verkoopmail.

    python3 schermafbeelding.py <uitmap> <slug> [<slug> ...]

Opent https://<slug>.tdswebstudio.nl op 1200×750, en schrijft <uitmap>/voorbeeld-<slug>.jpg
(720 px breed, JPEG kwaliteit 68, ongeveer 20–40 kB). Die plakt de afwerkronde in het Gmail-concept.
Nodig: playwright (chromium) en Pillow.
"""
import asyncio, os, sys

from PIL import Image
from playwright.async_api import async_playwright

DOMEIN = "tdswebstudio.nl"


async def maak(uitmap, slugs):
    os.makedirs(uitmap, exist_ok=True)
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        for slug in slugs:
            pagina = await browser.new_page(viewport={"width": 1200, "height": 750}, device_scale_factor=1)
            await pagina.goto(f"https://{slug}.{DOMEIN}/", wait_until="networkidle")
            await pagina.wait_for_timeout(800)
            ruw = os.path.join(uitmap, f"ruw-{slug}.png")
            await pagina.screenshot(path=ruw)
            await pagina.close()
            beeld = Image.open(ruw).convert("RGB")
            beeld = beeld.resize((720, round(beeld.height * 720 / beeld.width)), Image.LANCZOS)
            doel = os.path.join(uitmap, f"voorbeeld-{slug}.jpg")
            beeld.save(doel, quality=68, optimize=True)
            os.remove(ruw)
            print(doel, os.path.getsize(doel))
        await browser.close()


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    asyncio.run(maak(sys.argv[1], sys.argv[2:]))
