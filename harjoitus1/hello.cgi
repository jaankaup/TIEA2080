#!/usr/bin/python
# -*- coding: utf-8 -*-

import cgitb
import urllib2
import simplejson as json

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
def etsiJoukkueet():
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

def prettyPrint(parsedJSON):
    print json.dumps(parsedJSON, indent=4, sort_keys=True, ensure_ascii=False).encode("UTF-8")

#########################################################################

print u"""Content-type: text/plain; charset=UTF-8


"""
print u"T1 tason tulosteet".encode("UTF-8")
print u"Tulostetaan kilpailujen nimet seka niiden jasenet.".encode("UTF-8")
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
print u"""Nyt tulostetaan Jäärogaining joukkue, josta näkyy että uusijoukkue on
lisätty sinne""".encode("UTF-8")
prettyPrint(etsiKisa(u"Jäärogaining"))
