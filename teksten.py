"""teksten.py — voorstel-teksten per branche. Alles hier gaat over het vák, nooit over het
bedrijf: geen jaartallen, aantallen medewerkers, certificaten of beloftes die niet te
controleren zijn. Wat uit deze lijst komt, staat in NALOPEN.md als 'voorstel-tekst'.

Per branche: kop (met {plaats}), sub, diensten {naam: omschrijving}, waarom [(kop, tekst)],
cta (kop, tekst), knop.
"""
import re

ALGEMEEN = {
    "kop": "{naam}",
    "kop_plaats": "{naam} in {plaats}",
    "sub": "Vakwerk uit de buurt. Neem contact op voor een afspraak of een vrijblijvende prijsopgave.",
    "diensten": {},
    "waarom": [
        ("Eén aanspreekpunt", "Van eerste contact tot oplevering heeft u met dezelfde persoon te maken. U hoeft niet achter losse partijen aan."),
        ("Afspraak is afspraak", "Een duidelijke prijsopgave vooraf en een planning die we nakomen. Geen verrassingen achteraf."),
        ("Uit de regio", "Korte lijnen en snel ter plaatse, ook als er later nog een vraag is."),
    ],
    "cta": ("Iets voor u?", "Vertel kort wat u zoekt en we kijken samen wat er mogelijk is."),
    "knop": "Vraag een prijsopgave aan",
    "diensten_intro": "Hieronder staat waar we mee helpen.",
}

BRANCHES = {
    "hoveniers": {
        "kop_plaats": "Hovenier in {plaats} en omgeving",
        "sub": "Aanleg, renovatie en onderhoud van tuinen. Neem contact op voor een afspraak in de tuin.",
        "diensten": {
            "Tuinontwerp": "Een ontwerp op schaal, afgestemd op hoe u de tuin wilt gebruiken, met beplanting die past bij grond en licht.",
            "Tuinaanleg": "Bestrating, borders, gazon en verlichting in één hand. Wij regelen de afvoer van grond en de aanvoer van materiaal.",
            "Tuinrenovatie": "Een bestaande tuin opnieuw indelen zonder alles weg te halen: houden wat goed is, vervangen wat versleten is.",
            "Tuinonderhoud": "Snoeien, bemesten, onkruid en het gazon — op afspraak of met een vast onderhoudsplan door het jaar heen.",
            "Bestrating": "Terrassen, paden en opritten in klinkers, tegels of natuursteen, gelegd op een goed voorbereide ondergrond.",
            "Vlonders": "Vlonderterrassen in hardhout of composiet, met een onderconstructie die niet gaat werken.",
            "Vijvers": "Aanleg van vijvers met een werkend filtersysteem en de juiste waterplanten.",
            "Waterpartijen": "Waterpartijen, waterelementen en beekjes die bij de rest van de tuin passen en makkelijk te onderhouden zijn.",
            "Schuttingen en overkappingen": "Erfafscheidingen, schuttingen en veranda's die passen bij de stijl van huis en tuin.",
            "Beplanting": "Beplantingsplannen met soorten die het goed doen op uw grond en in uw lichtsituatie.",
        },
        "waarom": [
            ("Eén aanspreekpunt", "Van eerste schets tot oplevering loopt alles via dezelfde persoon. U hoeft niet achter losse partijen aan."),
            ("Vakwerk dat blijft liggen", "De ondergrond en de afwatering krijgen net zoveel aandacht als wat u ziet. Daar zit het verschil na een paar winters."),
            ("Uit de regio", "We kennen de grond en het klimaat hier, en zijn snel ter plaatse als er later nog een vraag is."),
        ],
        "cta": ("Een tuin in gedachten?", "Vertel wat u wilt en we kijken samen wat er mogelijk is."),
        "knop": "Vraag een offerte aan",
        "diensten_intro": "Werk in en om de tuin, van ontwerp tot onderhoud.",
    },
    "tuincentra": {
        "kop_plaats": "Tuincentrum in {plaats}",
        "sub": "Planten, bomen en alles voor de tuin, met advies van mensen die het zelf kweken en verzorgen.",
        "diensten": {
            "Tuinplanten": "Vaste planten, heesters en seizoensplanten, gekozen op wat het hier goed doet.",
            "Bomen en hagen": "Laan- en fruitbomen, haagplanten en leibomen in verschillende maten, met advies over plantafstand en snoei.",
            "Kamerplanten": "Groene en bloeiende kamerplanten met tips voor licht, water en voeding.",
            "Potterie en tuinmeubelen": "Potten, bakken en meubelen voor terras en balkon.",
            "Advies": "Vragen over bodem, bemesting, snoei of plagen? Loop binnen of stuur een foto.",
        },
        "cta": ("Vraag over uw tuin?", "Loop langs, bel of stuur een foto — we denken graag mee."),
        "knop": "Stel uw vraag",
    },
    "dakdekkers": {
        "kop_plaats": "Dakdekker in {plaats} en omgeving",
        "sub": "Platte en hellende daken: nieuw, gerepareerd of geïsoleerd. Ook bij lekkage snel ter plaatse.",
        "diensten": {
            "Platte daken": "Bitumen en EPDM dakbedekking, aangebracht op een goed afgeschoten ondergrond zodat water niet blijft staan.",
            "Hellende daken": "Pannendaken vernieuwen of herstellen, inclusief panlatten, folie en nokafwerking.",
            "Dakisolatie": "Isolatie van bovenaf of van binnenuit, afgestemd op de constructie en de subsidieregels.",
            "Lekkage en reparatie": "Opsporen en verhelpen van lekkages, ook als de oorzaak niet meteen zichtbaar is.",
            "Dakgoten en zinkwerk": "Goten, hemelwaterafvoer en zinkwerk vervangen of herstellen.",
            "Dakinspectie": "Een periodieke controle van het dak, met foto's en een advies over wat er wanneer moet gebeuren.",
        },
        "cta": ("Twijfel over uw dak?", "Een inspectie is zo gepland. Bij lekkage bellen we terug op de dag zelf."),
        "knop": "Vraag een dakinspectie aan",
    },
    "timmerbedrijven": {
        "kop_plaats": "Timmerbedrijf in {plaats} en omgeving",
        "sub": "Verbouw, aanbouw en maatwerk in hout. Van dakkapel tot keukenmontage.",
        "diensten": {
            "Verbouwingen": "Verbouwen en uitbreiden van woningen, inclusief afstemming met andere vakmensen.",
            "Aanbouw en uitbouw": "Meer ruimte aan huis, van fundering tot afwerking.",
            "Dakkapellen": "Dakkapellen op maat, in één dag geplaatst waar dat kan.",
            "Kozijnen en deuren": "Houten en kunststof kozijnen, ramen en deuren leveren en plaatsen.",
            "Interieur en maatwerk": "Kasten, trappen en inbouwoplossingen op maat gemaakt.",
            "Onderhoud": "Houtrot herstellen, schilderklaar maken en klein onderhoud aan de woning.",
        },
    },
    "schilders": {
        "kop_plaats": "Schildersbedrijf in {plaats} en omgeving",
        "sub": "Binnen- en buitenschilderwerk, behangen en houtrotherstel. Net werk, netjes achtergelaten.",
        "diensten": {
            "Buitenschilderwerk": "Kozijnen, deuren en gevels in de juiste opbouw van grond- tot aflaag, zodat het jaren meegaat.",
            "Binnenschilderwerk": "Wanden, plafonds en houtwerk, met aandacht voor het voorbereidende werk.",
            "Behangen": "Behang en glasvlies aanbrengen, ook op lastige ondergronden.",
            "Houtrotherstel": "Aangetast hout herstellen voordat er geschilderd wordt.",
            "Onderhoudsplan": "Een vast schema voor buitenonderhoud, zodat u nooit voor een grote beurt komt te staan.",
        },
    },
    "installateurs": {
        "kop_plaats": "Installatiebedrijf in {plaats} en omgeving",
        "sub": "Verwarming, sanitair, elektra en duurzame installaties. Voor storingen én voor verbouwingen.",
        "diensten": {
            "CV en verwarming": "Ketels, radiatoren en vloerverwarming plaatsen, onderhouden en repareren.",
            "Warmtepompen": "Advies over hybride of volledig elektrisch verwarmen, en de installatie ervan.",
            "Sanitair en badkamers": "Complete badkamers en toiletten, inclusief leidingwerk en afwerking.",
            "Elektra": "Groepenkasten, bedrading, verlichting en laadpalen, volgens de geldende normen.",
            "Zonnepanelen": "Zonnepanelen en omvormers, afgestemd op uw dak en verbruik.",
            "Storingen en onderhoud": "Snel ter plaatse bij storingen en jaarlijks onderhoud aan uw installatie.",
        },
    },
    "stukadoors": {
        "kop_plaats": "Stukadoor in {plaats} en omgeving",
        "sub": "Strakke wanden en plafonds, binnen en buiten. Ook sierpleister en spachtelputz.",
        "diensten": {
            "Wanden en plafonds": "Glad pleisterwerk, behang- of sausklaar opgeleverd.",
            "Sierpleister": "Spachtelputz, beton-ciré en andere decoratieve afwerkingen.",
            "Buitenstucwerk": "Gevels stuken en herstellen, met de juiste ondergrondbehandeling.",
            "Renovatie": "Oude wanden en plafonds herstellen en strak maken.",
        },
    },
    "kappers": {
        "kop_plaats": "Kapper in {plaats}",
        "sub": "Knippen, kleuren en stylen voor dames, heren en kinderen. Op afspraak, zodat u niet hoeft te wachten.",
        "diensten": {
            "Knippen": "Een coupe die bij u past en die thuis ook makkelijk goed valt.",
            "Kleuren": "Kleuringen, highlights en balayage met producten die het haar sparen.",
            "Stylen": "Föhnen en stylen voor elke dag of voor een speciale gelegenheid.",
            "Heren": "Knippen, baard en contouren.",
            "Kinderen": "Rustig en snel, zodat het voor de kleintjes leuk blijft.",
        },
        "cta": ("Afspraak maken?", "Bel, app of stuur een berichtje — we plannen een moment dat u schikt."),
        "knop": "Maak een afspraak",
    },
    "schoonheidssalons": {
        "kop_plaats": "Schoonheidssalon in {plaats}",
        "sub": "Gezichtsbehandelingen, huidverbetering en ontharen in een rustige salon.",
        "diensten": {
            "Gezichtsbehandeling": "Reiniging, verzorging en advies afgestemd op uw huidtype.",
            "Huidverbetering": "Behandelingen voor een egalere en frissere huid.",
            "Ontharen": "Harsen en andere methoden voor gezicht en lichaam.",
            "Wenkbrauwen en wimpers": "Epileren, verven en vormen.",
            "Pedicure en manicure": "Verzorging van handen en voeten.",
        },
        "cta": ("Afspraak maken?", "Bel of stuur een bericht — we plannen een moment dat u schikt."),
        "knop": "Maak een afspraak",
    },
    "fysiotherapeuten": {
        "kop_plaats": "Fysiotherapie in {plaats}",
        "sub": "Behandeling van klachten aan spieren en gewrichten, en begeleiding bij herstel. Zonder verwijzing welkom.",
        "diensten": {
            "Fysiotherapie": "Onderzoek, behandeling en oefeningen voor klachten aan rug, nek, schouder, knie en meer.",
            "Manuele therapie": "Gerichte behandeling van gewrichten bij beperkte beweeglijkheid.",
            "Revalidatie": "Begeleiding na een operatie of blessure, met een opbouwend programma.",
            "Sportfysiotherapie": "Behandeling en advies bij sportblessures en het voorkomen ervan.",
        },
        "cta": ("Een afspraak maken?", "Bel of gebruik het formulier. Een verwijzing is niet nodig."),
        "knop": "Maak een afspraak",
    },
    "autogarages": {
        "kop_plaats": "Autogarage in {plaats}",
        "sub": "Onderhoud, reparatie en APK voor alle merken. Eerlijk advies over wat wel en niet moet.",
        "diensten": {
            "APK": "Keuring met duidelijk overzicht van wat is afgekeurd en wat een advies is.",
            "Onderhoud": "Beurten volgens het schema van de fabrikant, met behoud van garantie.",
            "Reparatie": "Storingen opsporen en herstellen, van remmen tot elektronica.",
            "Banden": "Zomer-, winter- en all-seasonbanden, inclusief opslag.",
            "Airco": "Controle, bijvullen en reparatie van de airco.",
        },
        "cta": ("Afspraak maken?", "Bel of plan online. We laten vooraf weten wat het gaat kosten."),
        "knop": "Maak een afspraak",
    },
    "bakkers": {
        "kop_plaats": "Bakkerij in {plaats}",
        "sub": "Brood, banket en gebak, elke dag vers uit eigen bakkerij.",
        "diensten": {
            "Brood": "Dagelijks vers gebakken brood, van volkoren tot desem.",
            "Banket en gebak": "Taarten, gebakjes en koek voor elke dag en voor feesten.",
            "Bestellen": "Taarten en grotere bestellingen op maat, op afspraak.",
        },
        "cta": ("Bestellen?", "Bel of gebruik het formulier voor taarten en grotere bestellingen."),
        "knop": "Plaats een bestelling",
    },
    "restaurants": {
        "kop_plaats": "Restaurant in {plaats}",
        "sub": "Eten en drinken in een ontspannen sfeer. Reserveren kan telefonisch of via het formulier.",
        "diensten": {
            "Lunch": "Een kaart met broodjes, soepen en salades.",
            "Diner": "Een menu met seizoensgerechten en klassiekers.",
            "Groepen en feesten": "Ruimte voor groepen, met een menu in overleg.",
        },
        "cta": ("Reserveren?", "Bel of laat uw gegevens achter, dan bevestigen we de reservering."),
        "knop": "Reserveer een tafel",
    },
    "rijscholen": {
        "kop_plaats": "Rijschool in {plaats}",
        "sub": "Rijlessen in een rustig tempo, met een duidelijke planning richting het examen.",
        "diensten": {
            "Rijlessen auto": "Losse lessen of een pakket, met een proefles om te beginnen.",
            "Spoedopleiding": "In korte tijd naar het examen, met een intensief lesrooster.",
            "Faalangst": "Extra begeleiding voor wie zenuwen in de weg zitten.",
            "Theorie": "Hulp bij de voorbereiding op het theorie-examen.",
        },
        "cta": ("Proefles?", "Laat uw gegevens achter, dan plannen we een eerste les."),
        "knop": "Vraag een proefles aan",
    },
    "makelaars": {
        "kop_plaats": "Makelaar in {plaats} en omgeving",
        "sub": "Verkoop, aankoop en taxatie van woningen in de regio.",
        "diensten": {
            "Verkoop": "Van waardebepaling tot overdracht, inclusief fotografie en presentatie.",
            "Aankoop": "Begeleiding bij het zoeken, bezichtigen en onderhandelen.",
            "Taxatie": "Gevalideerde taxatierapporten voor hypotheek of verkoop.",
        },
        "cta": ("Uw woning verkopen?", "Vraag een vrijblijvende waardebepaling aan."),
        "knop": "Vraag een waardebepaling aan",
    },
}

# aliassen: dienst-namen van de bestaande site koppelen aan onze omschrijvingen
ALIAS = {
    "tuinaanleg": "Tuinaanleg", "aanleg": "Tuinaanleg", "tuinontwerp": "Tuinontwerp", "ontwerp": "Tuinontwerp",
    "onderhoud": "Tuinonderhoud", "tuinonderhoud": "Tuinonderhoud", "renovatie": "Tuinrenovatie", "tuinrenovatie": "Tuinrenovatie",
    "bestrating": "Bestrating", "sierbestrating": "Bestrating", "vlonder": "Vlonders", "vlonders": "Vlonders", "vijver": "Vijvers",
    "vijvers": "Vijvers", "water": "Waterpartijen", "waterpartij": "Waterpartijen", "waterpartijen": "Waterpartijen",
    "schutting": "Schuttingen en overkappingen", "schuttingen": "Schuttingen en overkappingen", "overkapping": "Schuttingen en overkappingen",
    "beplanting": "Beplanting", "beplantingsplan": "Beplanting", "snoeien": "Tuinonderhoud",
}


def voor(branche):
    """Volledige tekstset voor een branche (algemeen aangevuld met branche-specifiek)."""
    t = dict(ALGEMEEN)
    t.update(BRANCHES.get(branche or "", {}))
    return t


def koppel_diensten(eigen_namen, branche, maximum=6):
    """Diensten van de bestaande site koppelen aan omschrijvingen. Geeft [(naam, tekst, bron)]
    met bron 'site' (naam van hun site) of 'voorstel' (uit teksten.py)."""
    t = voor(branche)
    uit = []
    for naam in eigen_namen:
        sl = naam.strip().lower()
        doel = ALIAS.get(sl) or next((k for k in t["diensten"] if k.lower() == sl), None)
        if not doel:
            doel = next((k for k in t["diensten"] if sl in k.lower() or k.lower() in sl), None)
        if not doel:
            # samengestelde namen: "Advies en Ontwerp", "Kappen/Rooien van bomen"
            for deel in re.split(r"\s+(?:en|&|/|,)\s+|/", sl):
                deel = re.sub(r"\b(van|de|het|en|uw)\b", " ", deel).strip()
                for w in [deel] + deel.split():
                    d2 = ALIAS.get(w) or next((k for k in t["diensten"] if w and (w == k.lower() or (len(w) > 4 and (w in k.lower() or k.lower() in w)))), None)
                    if d2:
                        doel = d2; break
                if doel:
                    break
        if doel and doel in t["diensten"]:
            uit.append((naam.strip(), t["diensten"][doel], "site+voorstel"))
        else:
            uit.append((naam.strip(), f"Vraag naar de mogelijkheden voor {naam.strip().lower()}; we vertellen graag wat erbij komt kijken.", "site"))
    if len(uit) < 3:
        for k, v in t["diensten"].items():
            if len(uit) >= maximum:
                break
            if not any(k.lower() == u[0].lower() for u in uit):
                uit.append((k, v, "voorstel"))
    return uit[:maximum]
