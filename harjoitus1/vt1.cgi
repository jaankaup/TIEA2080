#!/usr/bin/python
# -*- coding: utf-8 -*-

import cgitb
import urllib2
import simplejson as json
from math import sin, cos, sqrt, atan2, radians
from datetime import datetime

cgitb.enable()

# Haetaan data
response = urllib2.urlopen('http://appro.mit.jyu.fi/tiea2080/vt/vt1/data.json')
data = response.read()#.encode("UTF-8")
data2 = json.loads(data)

# Funktio, joka tulostaa kilpailujen nimet seka kilpailujen joukueiden
# jasenten nimet.
def tulostaKisaJaJasenet(d):
    for x in d:
        print x[u"nimi"].encode("UTF-8")
        try:
            for sarja in x["sarjat"]:
                for joukkue in sarja[u"joukkueet"]:
                    print (u"    " + joukkue[u"nimi"]).encode("UTF-8")
        except:
            pass

#########################################################################

# Etsii kisoista ensimmaisen, jonka nimi on kisaNimi, tai muuloin heittaa
# poikkeuksen.
def etsiKisa(kisaNimi):

    # Haetaan ne kisat, jossa on nimi on kisaNimi.
    kisat = [k for k in data2 if k[u"nimi"] == kisaNimi]
    if len(kisat) > 0:
        return kisat[0]

    raise Exception(u"Ei loytynyt kisaa nimella." + kisaNimi)

#########################################################################

# Etsii kaikki joukkueet.
def haeJoukkueet():
    # Haetaan ne kisat, jossa on sarjat.
    kisat = filter(lambda x: u"sarjat" in x, [k for k in data2])

    # Haetaan kustakin kisata sarjat, joissa on joukkueet.
    sarjat = [sarja for k in kisat for sarja in k[u"sarjat"] if 'joukkueet' in
            sarja] 

    # Kerataan joukkueet listaan.
    joukkueet = [j for s in sarjat for j in s[u"joukkueet"]]

    # Palautetaan joukkueet
    return joukkueet

#########################################################################

def haeSarjat():

    # Haetaan ne kisat, jossa on sarjat.
    kisat = filter(lambda x: u"sarjat" in x, [k for k in data2])

    # Haetaan jokaisesta kisasta kaikki sarjat.
    sarjat = [s for x in kisat for s in x[u"sarjat"]]
    return sarjat

#########################################################################

# Haetaan numerolla alkavat koodit @rastit listasta.
def haeNumberKoodit(rastit):

    # Haetaan ne rastit, joden koodi alkaa numerolla.
    koodit = haeRastitWithNumberCode(rastit)

    # Otetaan koodit talteen.
    numberKoodit = sorted(map(lambda y: y[u"koodi"], koodit))

    return numberKoodit

#########################################################################

# Etsii sarjan kaikkien kisojen joukosta. @sarja on sarjan id ja @sarjanNimi on sarjan nimi.
# Etsii ensin id:n perusteella, jos ei loydy, niin etsii nimen perusteella.
# Palauttaa ensimmaisen sarjan, joka vastaa hakua. jos sarjaa ei loydy, niin
# heittaa poikkeuksen.
def etsiSarja(sarja, sarjanNimi):

    # Haetaan ne kisat, jossa on sarjat.
    kisat = filter(lambda x: u"sarjat" in x, [k for k in data2])

    # Etsitaan sarjaa id:n perusteella. Palautetaan ensimmainen niista.
    loytynyt = [s for k in kisat for s in k[u"sarjat"] if s[u"id"] == sarja]
    if len(loytynyt) != 0: return loytynyt[0]

    # Etsitaan sarjaa nimen perusteella. Jos sellaisia loytyy, niin palautetaan
    # ensimmainen.
    loytynyt = [s for k in kisat for s in k[u"sarjat"] if s[u"nimi"] == sarjanNimi]
    if len(loytynyt) != 0: return loytynyt[0]

    raise Exception(u"Ei loytynyt sarjaa.")

#########################################################################

def haeRastit():

    # Haetaan ne kisat, jossa on rastit.
    kisat = filter(lambda x: u"rastit" in x, [k for k in data2])
    rastit = [x for k in kisat for x in k[u"rastit"]]
    return rastit

#########################################################################

# Filteroidaan ne rastit, joissa koodi alkaa numerolla.
def haeRastitWithNumberCode(rastit):

    # Haetaan ne rastit, joden koodi alkaa numerolla.
    rkoodit = filter(lambda x: x != None and len(x[u"koodi"]) > 0 and
            x[u"koodi"][0].isdigit(), rastit)

    return rkoodit;

#########################################################################

def lisaaJoukkue(joukkue, kisaNimi, sarjanNimi):

    # Etsitaan kisa.
    try:
        kisa = etsiKisa(kisaNimi)
    except:
        print (u"lisaaJoukkue: kisaa ei loydy nimella" +
                kisaNimi).encode("UTF-8")
        return

    # Etsitaan sarja.
    try:
        sarjat = [x for x in kisa[u"sarjat"] if x[u"nimi"] ==
                sarjanNimi]
        if len(sarjat) > 0: sarjat[0][u"joukkueet"].append(joukkue)
    except:
        print u"lisaaJoukkue: joukkueen lisays epaonnistui.".encode("UTF-8")
        print u"sarjat:".encode("UTF-8")
        print sarjat

#########################################################################

# funktio, joka poistaa annetulta sarjalta kaikki @joukkueNimi nimiset
# joukkueet.
def poistaJoukkue(sarja, joukkueNimi):

    # Haetaan kaikki sarjat.
    sarjat = haeSarjat()

    # Etsitaan argumenttina tuotua sarjaa sarjojen joukosta.
    found = None
    for x in sarjat:
        if sarja is x:
            found = x
            break

    # Jos sarjaa ei loydy, niin ei tehda mitaan.
    if found == None:
        return

    # Etsitaan sarjasta joukkueet, joiden nimi ei ole @joukueNimi
    joukkueet = [x for x in found[u"joukkueet"] if x[u"nimi"] != joukkueNimi]

    # Asetetaan edellinen lista, josta poistettu @joukkueNimi:set joukkueet 
    # sarjaan.
    found[u"joukkueet"] = joukkueet

#########################################################################

# Funktio, joka hakee joukkueen nimen perusteella. Hakee vain ensimmaisen
# loydetyn joukkueen. Jos joukkuetta ei loyty, palautetaan None.
def haeJoukkueByName(joukkueNimi):
    joukkueet = haeJoukkueet()
    j = [x for x in joukkueet if x[u"nimi"] == joukkueNimi]
    if len(j) == 0: return None
    return j[0]

#########################################################################

def haeTuvat():

    # Haetaan ne kisat, jossa on tuvat.
    kisat = filter(lambda x: u"tupa" in x, [k for k in data2])

    # Haetaan kaikki tuvat.
    tuvat = [t for k in kisat for t in k[u"tupa"]]

    return tuvat

#########################################################################

# Hakee kaikki joukkueen tuvat.
def haeTuvatByJoukkue(joukkue):

    # Haetaan tuvat.
    tuvat = haeTuvat()

    # Filteroidaan te tuvat, jotka kuuluvat joukkueelle.
    tuvatJoukkue = filter(lambda x: x[u"joukkue"] == joukkue[u"id"], tuvat)

    return tuvatJoukkue

#########################################################################

def getMatka(joukkue):

    # haetaan kaikki rastit ja joukkueen tuvat.
    rastit = haeRastit()
    tuvat = haeTuvatByJoukkue(joukkue)

    # jarjestetaan tuvat ajan mukaan.

    # Poistetaan tuvat, jossa ei ole kunnollista aikaa.
    timeless = filter(lambda x: luoAika(x[u"aika"]) != None, tuvat)

    sortatutTuvat = sorted(timeless, key=lambda x: luoAika(x[u"aika"]))

    sortatutRastit = [tupaToRasti(x[u"rasti"], rastit) for x in sortatutTuvat]

    nonetPoistettu = filter(lambda x: x != None, sortatutRastit)

    # Tehdaan lat lon pareja.
    lonlatit = map(lambda x: (float(x[u"lat"]),float(x[u"lon"])), nonetPoistettu)

    # Lasketaan matka!
    summa = 0.0

    if len(lonlatit) < 2: return summa

    edellinen = lonlatit[0]

    for (lat,lon) in lonlatit:
       summa += laskeMatka(edellinen[0],edellinen[1],lat,lon)
       edellinen = (lat,lon)

    return int(round(summa,0))


#########################################################################

def getKokonaisaika(joukkue):

    # haetaan kaikki rastit ja joukkueen tuvat.
    rastit = haeRastit()
    tuvat = haeTuvatByJoukkue(joukkue)

    # Poistetaan tuvat, jossa ei ole kunnollista aikaa.
    timeless = filter(lambda x: luoAika(x[u"aika"]) != None, tuvat)

    # otetaan ajat talteen ja luodaan niista datetime olioita.
    sortatutAjat = sorted([luoAika(x[u"aika"]) for x in timeless])

    # Palautetaan viimeisen ja ensimmaisen ajan erotus, tai aika 0 muutoin.
    if len(sortatutAjat) > 1:
        return sortatutAjat[len(sortatutAjat)-1] - sortatutAjat[0]
    return None

#########################################################################

# Funktio, joka ottaa argumenttina rastiId:n ja palauttaa sita vastaavan
# rastin, tai sitten palauttaa None. "Tehokkuus syista" paramerina myos rastit
# lista.
def tupaToRasti(rastiId, rastit):
    rasti = filter(lambda x: unicode(x[u"id"]) == unicode(rastiId), rastit)
    if len(rasti) == 0: return None
    return rasti[0]

#########################################################################

def laskePisteet(joukkue):

    # haetaan kaikki rastit ja joukkueen tuvat.
    rastit = haeRastit()
    tuvat = haeTuvatByJoukkue(joukkue)

    # poistetaan monkikot.
    tupaset = list(set([unicode(t[u"rasti"]) for t in tuvat]))

    # haetaan oikeat rastit-oliot, jottaa saadaan koodit.
    rastitNoMonikerta = map(lambda x: tupaToRasti(x,rastit),tupaset)
    nonetPoistettu = filter(lambda x: x != None, rastitNoMonikerta)

    # Haetaan koodit.
    koodit = haeNumberKoodit(nonetPoistettu)

    # Lasketaan pisteet yhteen.
    summa = sum([int(x[0]) for x in koodit])

    return summa

#########################################################################

def prettyPrint(parsedJSON):
    print json.dumps(parsedJSON, indent=4, sort_keys=True, ensure_ascii=False).encode("UTF-8")

#########################################################################

# Luo daten vvvv-kk-pp dd:dd:dd muotoisesta datasta.
def luoAika(uStr):
    try:
        return datetime.strptime(uStr,u"%Y-%m-%d %H:%M:%S")
    except:
        return None

#########################################################################

# Matkittu netista.
def laskeMatka(lat1,lon1,lat2,lon2):

    R = 6373.0
    rlat1 = radians(lat1)
    rlon1 = radians(lon1)
    rlat2 = radians(lat2)
    rlon2 = radians(lon2)
    rdlon = rlon2 - rlon1
    rdlat = rlat2 - rlat1
    a = sin(rdlat / 2)**2 + cos(rlat1) * cos(rlat2) * sin(rdlon / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c

#########################################################################

# Tulostaa taso5:sen.
def tulostaTaso5():
    joukkueet = haeJoukkueet()
    kokoHomma = [(x[u"nimi"],getKokonaisaika(x),getMatka(x),laskePisteet(x)) for x in joukkueet]
    epoch = datetime.fromtimestamp(0) - datetime.fromtimestamp(0)
    sortattu = sorted(kokoHomma, key=lambda x: x[3],reverse=True)
    for x in sortattu:
        time = u"0:00:00" if x[1] == None else unicode(x[1])
        print (unicode(x[0]) + u",").encode("UTF-8"),
        print (unicode(x[2]) + u" km, ").encode("UTF-8"),
        print (unicode(x[3]) + u" p, ").encode("UTF-8"),
        print (time).encode("UTF-8")

#########################################################################

print u"""Content-type: text/plain; charset=UTF-8


"""
print u"T1 tason tulosteet".encode("UTF-8")
print u"Tulostetaan kilpailujen nimet seka niiden joukkueiden nimet.".encode("UTF-8")
print u"".encode("UTF-8")
tulostaKisaJaJasenet(data2)
print u"".encode("UTF-8")
print u"Lisataan tason 1 mukainen joukkue.".encode("UTF-8")
joukkue1 = {
        "nimi": u"Mallijoukkue",
        "jasenet": [
            u"Tommi Lahtonen",
            u"Matti Meikäläinen"
            ],
        "seura": None,
        "id": 99999
        }
lisaaJoukkue(joukkue1,u"Jäärogaining","4h")
print u""
print u"Tulostetaan kaikki joukkueet. Mukana nyt myos mallijoukkue.".encode("UTF-8")
print u""
for x in haeJoukkueet(): print x[u"nimi"].encode("UTF-8") 
print u""
#prettyPrint(haeSarjat())
print u";".join(haeNumberKoodit(haeRastit())).encode("UTF-8")
print u""
print u"T3 tason tulosteet".encode("UTF-8")
print u""
print u"Poistetaan Vapaat, Vara 1 ja Vara 2 nimiset joukkueet.".encode("UTF-8")
poistaJoukkue(etsiSarja(4751022794735616,u"blaaah"), u"Vapaat")
poistaJoukkue(etsiSarja(5639189416640512,u"blaaah"), u"Vara 1")
poistaJoukkue(etsiSarja(5639189416640512,u"blaaah"), u"Vara 2")
print u""
print u"Tulostetaan kaikki joukkueet. Nyt Vapaat, Vara 1 ja Vara 2 poistettu.".encode("UTF-8")
for x in haeJoukkueet(): print x[u"nimi"].encode("UTF-8") 
print u""
print u"Tulostetaan taso 5..".encode("UTF-8")
print u""
tulostaTaso5()
