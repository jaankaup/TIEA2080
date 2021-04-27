#!/usr/bin/python
# -*- coding: utf-8 -*-

# form accept-encoding="UTF-8"
import cgitb
import urllib
import os
import cgi
import simplejson as json
from jinja2 import Template, Environment, FileSystemLoader

# Enabloidaan pythonin virheilmoitusten nakyminen selaimessa.
cgitb.enable()

# Tulostetaan html-protokollan vaatima mediatyyppi.
print u"""Content-type: text/html; charset=UTF-8\n""".encode("UTF-8")

##############################################################################

# Kloona pelin. qr tuli alunperin nimesta queryString.
def clone(qr):
    return {u"x": qr[u"x"],
            u"teksti": qr[u"teksti"],
            u"ruutu": qr[u"ruutu"],
            u"tila": qr[u"tila"],
            u"rakenne": list(qr[u"rakenne"])}

##############################################################################

# Piirtaa html:n.
def renderGame(qr, error, url):
    siirraQS = clone(qr)
    siirraQS[u"ruutu"] = u"siirra"
    poistaQS = clone(qr)
    poistaQS[u"ruutu"] = u"poista"
    siirraUrl = createNewUrl(url,convertTaulukkoToStr(qr[u"rakenne"],url,siirraQS))
    poistaUrl = createNewUrl(url,convertTaulukkoToStr(qr[u"rakenne"],url,poistaQS))
    print template.render(teksti=qr[u"teksti"],
                          x=qr[u"x"],
                          taulukko=convertTaulukko(qr[u"rakenne"], url, qr),
                          poistaHref=poistaUrl,
                          siirraHref=siirraUrl,
                          r=u"r",
                          b=u"b",
                          gr=u"R", # vihrea, aikaisemmin r
                          gb=u"B", # vihrea, aikasemmin b
                          e=u"e",
                          tila= qr[u"tila"],
                          virheIlmoitus=error).encode("UTF-8")

##############################################################################

# Luo uuden pelin (dictin)
def createGame(qr):
    newQR = clone(qr)
    # Jos ei ole mitaan rakennetta tai painettu uusi, niin...
    if len(newQR[u"rakenne"]) == 0:
        return createNewGame(newQR)

    # Jos painetaan Poistotilaa. TODO: Palauta virhea pallukka normaaliksi.
    elif newQR[u"ruutu"] == u"poista":

        # Mutetaan tila poistaksi.
        newQR[u"tila"] = u"poista"
        # Muutetaan virhea pallukka takaisin entisenvariseksi.
        newQR[u"rakenne"] = [x.lower() if x == u"R" or x == u"B" else x for x in newQR[u"rakenne"]]

    # Jos painetaan Siirtotila.
    elif newQR[u"ruutu"] == u"siirra":
        # Muutetaan tila siirraksi.
        newQR[u"tila"] = u"siirra"

    # Jos painetaan jotain ruutua (numero-indeksi).
    elif qr[u"ruutu"].isdigit():
        index = int(qr[u"ruutu"])

        # Jos tila on poista, niin poistetaan nappula.
        if newQR[u"tila"] == u"poista":
            poistaNappula(newQR[u"rakenne"],index)

        # Jos tila on siirra, niin...
        elif newQR[u"tila"] == u"siirra":

            # Etsitaan onko jo entuudestaan vihreaa nappia.
            vihrea = None
            for (i,e) in enumerate(newQR[u"rakenne"]):
                if e == (u"R") or e == u"B":
                    vihrea = (i,e)
                    break
            # Ei loytynyt vihreaa nappulaa entuudestaan, joten nyt on.
            if vihrea is None:
                newColor = newQR[u"rakenne"][index]
                # Paitsi jos yritetaan valita tyhjaa ruutua...
                if newColor == u"e":
                    return newQR
                # Ei ole tyhja ruutu. Nyt siis muutetaa vihreaksi.
                newColor = newQR[u"rakenne"][index].upper()
                newQR[u"rakenne"][index] = newColor

            # Vihrea palluka loytyi. Tehdaan siirto.
            else:
                siirraNappula(newQR[u"rakenne"], vihrea[0], index)

    return newQR

##############################################################################

# Luo uuden pelin x:n ja tekstin perusteella.
def createNewGame(qr):
    newQR = clone(qr)
    newQR[u"rakenne"] = luoTaulukko(qr[u"x"])
    newQR[u"tila"] = u"poista"
    newQR[u"ruutu"] = u""
    return newQR

##############################################################################

# Apufunktio, joka updatettaa dictin, ja palauttaa sen samantien.
def addToDict(d,e):
    d.update(e)
    return d

##############################################################################

# Tehdaan lista, jossa on kirjaimella merkitty mita missakin solussa on.
# koko on taulukon dimension koko.
# Palauttaa koko*koko taulukon, jossa on jokainen taulukon alkio on 
# joko u"b", u"r" tai u"e". Kts. varien sijoittuminen tiea2080 
# tehtavanannosta. jos jotain menee pieleen, niin palautetaan None.
# Lisataan varin lisaksi href. Eli palautaa tuplen listan (osoite, vari)
# alkioita.
def luoTaulukko(koko):
    try:
        #finalTaulukko = []
        taulukko = [u"b" if xCoord - yCoord == 0 else u"r" if xCoord+
                yCoord == koko-1 else u"e" for yCoord in range(0,koko) for xCoord in
                range(0,koko)]
        return taulukko
    except Exception as e:
        print u"luoTaulukko()".encode("UTF-8")
        print unicode(e).encode("UTF-8")
        return None;

##############################################################################

def poistaNappula(taulukko, index):
    taulukko[index] = u"e"

##############################################################################

def lisaaNappula(taulukko, index, char):
    taulukko[index] = char

##############################################################################

def siirraNappula(taulukko, oldIndex, newIndex):

    newChar = taulukko[newIndex]
    oldChar = taulukko[oldIndex]

    # Jos uusi indeksi ei ole tyhja ruutu, niin muutetaan 
    # uusi indeksi vihreaksi ja vanha indeksi vanhan variseksi.
    if newChar != u"e":
        taulukko[newIndex] = newChar.upper()
        taulukko[oldIndex] = oldChar.lower()
        return

    taulukko[newIndex] = taulukko[oldIndex].lower()
    # Muutetaan pelilaudan vanhaindeksi tyhjaksi.

    # Jos vanha indeksi ja uusi indeksi samoja ovat erit, niin 
    # poistetaan vanhan pelilaudan ruudun sisalto.
    if oldIndex != newIndex:
        taulukko[oldIndex] = u"e"

##############################################################################

def convertTaulukkoToStr(t,url,qr):
        qrDict = clone(qr)
        qrDict[u"rakenne"] = json.dumps(t,encoding='utf-8',separators=(u',',u':')).replace(u"\"",u"").replace(u",",u"").replace(u"[",u"").replace(u"]",u"")
        return qrDict

##############################################################################

# Konvertoi luoTaulukko-funktion mukaisen taulukon siten, etta jokainen solu 
# muuttuu nyt hrefiksi shakki-taulukon elementteja varten.
def convertTaulukko(t,url,qr):
        qrDict = convertTaulukkoToStr(t,url,qr)

        # Indeksoidaan ruudukon alkiot.
        taulukkoUrl = [(createNewUrl(url,addToDict(qrDict,{u"ruutu": unicode(a)})),b)
                for a,b in enumerate(t)]
        return taulukkoUrl

##############################################################################

# Luodaan url, jossa on nyt myos queryString. url on unicode merkkijono
# ohjelman urlista, ja qsDict on dict, jossa on queryStringit osina.
def createNewUrl(url, qsDict):
    # prkl!!! Ei pitaisi vissiin kayttaa unicodeja dicktien keyna.
    uusiDict = {}
    for k,v in qsDict.items():
        uusiDict[k.encode("UTF-8")] = urllib.quote_plus(unicode(v).encode("UTF-8"))
    newQueryString = urllib.urlencode(uusiDict)
    return url + newQueryString

##############################################################################

try:
    tmpl_path = os.path.join(os.path.dirname(os.environ[u'SCRIPT_FILENAME']),u'templates')
except:
    tmpl_path = u"templates"

# alustetaan Jinja sopivilla asetuksilla
env = Environment(autoescape=True, loader=FileSystemLoader(tmpl_path), extensions=['jinja2.ext.autoescape'])

# ladataan oma template
template = env.get_template(u"vt2.html")

# Alustetaan lomake olio.
form = cgi.FieldStorage()

myurl = u"vt2.cgi?"

# Tahan tulevat ohjelman argumentit.
x = form.getfirst(u"x", u"8").decode("UTF-8")
teksti = urllib.unquote_plus(form.getfirst(u"teksti", u"")).decode("UTF-8")
ruutu = form.getfirst(u"ruutu", u"").decode("UTF-8")
tila = form.getfirst(u"tila", u"").decode("UTF-8")
rakenne = form.getfirst(u"rakenne", u"[]").decode("UTF-8")

if rakenne == u"[]": rakenne = json.loads(rakenne)
else: rakenne = [unicode(b) for b in rakenne]


# Asetetaan shakkikentan oletusarvoksi mahdollisimman pieni luku.
defaultX = 0
finalX = defaultX
virheIlmoitus = u""

try:
    parsedX = int(x)
    if parsedX < 8:
        virheIlmoitus = u"Antamasi luku " + unicode(parsedX) + u" on liian pieni. Anna numero väliltä 8-150";
    elif parsedX > 150:
        virheIlmoitus = u"Antamasi luku " + unicode(parserX) + u" on liian suuri. Anna numero väliltä 8-150";
    else:
        virheIlmoitus = u"";
        finalX = parsedX
except:
    virheIlmoitus = u"Et antanut kunnon lukua. Anna luku väliltä 8-150.";

qr = {u"x":finalX, u"teksti":teksti,u"ruutu":ruutu, u"tila": tila, u"rakenne":rakenne}

game = createGame(qr)
renderGame(game,virheIlmoitus,myurl)
