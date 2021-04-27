#!/usr/bin/python
# -*- coding: utf-8 -*-

import io
import imp
import inspect
from functools import wraps
import json
import logging
import random

logging.basicConfig(filename=u'../../../../flaskLog/flask.log', level=logging.DEBUG)

tags = {'kilpailu':0, 'sarja':1, 'joukkue':2, 'rasti':3}

# Tassa on kaikki tarvittava tietokannan hakuun vt3 varten.

#########################################################################

# Oma debuggausta helpottava apufunktio.
def debug(msg):
    toPrint = u"{0} : {1}".format(inspect.stack()[1][3], msg)
    try:
        imp.find_module('logging')
        logging.debug(toPrint)
    except:
        print toPrint

###############################################################################

# Wrapperi funktio, joka avaa data.json tiedoston ja purkaa sielta datan 
# ja kutsuu sitten wrapattya funktiota. Toisaalta jos data on maaritelty jo 
# kutsuvaiheessa, niin silloin ei ladata dataa tiedostosta vaan kaytetaan 
# argumenttina annettua dataa.
# Esim. haeJoukkueet() => haetaan data tiedostosta.
#       haeJoukkueet(data=munData) => kaytetaan munDataa eika tiedostosta
#       haettua.
# Helpottaa 1-demossa kaytettyja apufunktioia.
def fileOpener(f):
    @wraps(f)
    def wrapper(*args, **kwds):
        data = None
        d = [v for k,v in kwds.iteritems() if k == u"data"]

        # Katsotaan loytyyko argumenttilista data.
        if len(d) == 1:
            # Poistetaan data.
            kwds.pop('data',None)
            # Otetaan data talteen data-muuttujaan.
            data = d[0]
        # Ei loytynyt, joten haetaan data tiedostosta.
        else:
            with open(u"../../../../flaskLog/data.json", 'r') as file:
                data = json.loads(file.read())
        # Kutsutaan wrapattya funtiota.
        return f(data=data,*args, **kwds)
    return wrapper

#########################################################################

# Funktio, joka tallentaan datan.
def saveData(data):
    try:
        with open(u"../../../../flaskLog/data.json", 'w') as file:
            file.write(json.dumps(data))
    except Exception as e:
        debug(e)

#########################################################################

# Hakee rastit ja kunkin rastin leimauslukumaaran annetusta kisasta.
@fileOpener
def getRastit(kId,data=None):

    kisa = None

    for k in data:
        if kId == k['id']:
            kisa = k

    if kisa is None: return []

    rastit = []

    if 'rastit' in kisa:
        rastit = kisa['rastit']

    if 'tupa' not in kisa:
        kisa['tupa'] = []

    tuvat = []

    for x in kisa['tupa']:
        try:
            tuvat.append(int(x['rasti']))
        except:
            pass
    
    # Lasketaan rastileimauksien lkm kullekin rastille.
    for r in rastit:
        r['lkm'] = len(filter(lambda x: r['id'] == x, tuvat))

    rastit.sort(key=lambda x: x['koodi'])

    return rastit

#########################################################################

@fileOpener
def getJoukkueByNimi(nimi,data=None):
    nimi = nimi.strip()
    for k in data:
        if 'sarjat' in k:
            for s in k['sarjat']:
                if 'joukkueet' in s:
                    for j in s['joukkueet']:
                        if j['nimi'].strip() == nimi:
                            j['sarja'] = s['id']
                            j['salasana'] = u""
                            return j
    return None

#########################################################################

@fileOpener
def getJoukkueById(jid,data=None):
    for k in data:
        if 'sarjat' in k:
            for s in k['sarjat']:
                if 'joukkueet' in s:
                    for j in s['joukkueet']:
                        if j['id'] == jid:
                            j['sarja'] = s['id']
                            j['salasana'] = u""
                            return j
    return None

#########################################################################

@fileOpener
def tallennaJoukkue(joukkue,data=None):
    sarja = None
    for k in data:
        if 'sarjat' in k:
            for s in k['sarjat']:
                if joukkue['sarja'] == s['id']:
                    sarja = s
    if sarja is None:
        debug(u"Joukkueen tallennus epaonnistui.")
        debug(u"Ei loydy sarjaa mihin tallentaa.")
        return

    # Ripataan sarja pois. Pop olisi ollut parempi...
    sarja['joukkueet'].append({'id':createUniqueId('joukkue'),
                               'nimi':joukkue['nimi'],
                               'last': u"1967-11-11 13:12:11",
                               'jasenet': json.loads(joukkue['jasenet'])})

    saveData(data)

#########################################################################

@fileOpener
def tallennaTupa(rId,jId,aika,data=None):
    kisa = None
    for k in data:
        if 'sarjat' in k:
            for s in k['sarjat']:
                if 'joukkueet' in s:
                    for j in s['joukkueet']:
                        if j['id'] == jId:
                            kisa = k
                            if 'tupa' not in kisa:
                                kisa['tupa'] = []
                            break
    if kisa is None:
        debug(u"Tupaa ei voitu tallnentaa. Kisa ei loydy.")
        return

    if 'tupa' not in kisa:
        debug(u"Tupaa ei voitu tallentaa. Tupaa ei loydy.")
        return
    kisa['tupa'].append({'aika':aika,'joukkue':jId,'rasti':rId})
    saveData(data)

#########################################################################

@fileOpener
def tallennaRasti(rasti,data=None):
#                db.tallennaRasti({'lat': lat, 'lon': lon, 'koodi': tempKoodi,'kilpailu': session['adminKilpailu']['id']})
    for k in data:
        if k['id'] == rasti['kilpailu']:
            if 'rastit' not in k:
                k['rastit'] = []
            uusiId = None
            if 'id' not in rasti:
                uusiId = createUniqueId(u"rasti")
            else:
                uusiId = rasti['id']
            k['rastit'].append({'lat': rasti['lat'],
                                'lon': rasti['lon'],
                                'koodi': rasti['koodi'],
                                'id': uusiId})
            debug({'lat': rasti['lat'],
                   'lon': rasti['lon'],
                   'koodi': rasti['koodi'],
                   'id': createUniqueId(u'rasti')})
            saveData(data)
            return

#########################################################################

@fileOpener
def poistaTupa(tupa,data=None):
    for k in data:
        if 'tupa' in k:
            for x in range(len(k['tupa'])):
                try:
                    if int(k['tupa'][x]['rasti']) == tupa['rId'] and k['tupa'][x]['joukkue'] == tupa['jId'] and k['tupa'][x]['aika'] == tupa['aika']:
                        del(k['tupa'][x])
                        saveData(data)
                        return
                except:
                    pass
    # TODO: testaa

#########################################################################

@fileOpener
def muokkaaTupa(vanhaTupa,rId,jId,aika,data=None):
    poistaTupa(vanhaTupa,data=data)
    tallennaTupa(rId,jId,aika,data=data)
    saveData(data)

#########################################################################

@fileOpener
def getJoukkueetBySarjaId(sId,data=None):
    joukkueet = []
    for k in data:
        if 'sarjat' in k:
            for s in k['sarjat']:
                if s['id'] == sId:
                    if 'joukkueet' in s:
                        joukkueet = s['joukkueet']
                    break
    for x in joukkueet:
        x['sarja'] = sId
    return joukkueet

#########################################################################

@fileOpener
def getKilpailu(joukkueId,data=None):
    for k in data:
        if 'sarjat' in k:
            for s in k['sarjat']:
                if 'joukkueet' in s:
                    for j in s['joukkueet']:
                        if j['id'] == joukkueId:
                            return {'id': k['id'],'nimi':k['nimi']}
    return None

#########################################################################

@fileOpener
def getKilpailuByNimi(kilpailuNimi,data=None):
    for k in data:
        if k['nimi'] == kilpailuNimi:
            return {'id': k['id'],'nimi':k['nimi']}
    return None

#########################################################################

@fileOpener
def getKilpailut(data=None):
    kilpailut = []
    for k in data:
        kilpailut.append({'id': k['id'],'nimi':k['nimi']})
    return kilpailut

#########################################################################

@fileOpener
def getDataToJoukkuelistaus(kilpailunNimi,data=None):

    result = []
    kisa = None

    for k in data:
        if k['nimi'] == kilpailunNimi:
            kisa = k

    if kisa is None:
        debug(u"kisaa ei loytynyt")
        return []

    if 'sarjat' not in kisa:
        debug(u"Kisalla ei ole sarjoja")
        return []

    for s in kisa['sarjat']:
        sarja = {'sNimi': s['nimi']}
        sData = []
        if 'joukkueet' in s:
            for j in s['joukkueet']:
                sData.append({'jNimi':j['nimi'],'jasenet':sorted(j['jasenet'])})
        sData.sort(key=lambda x: x['jNimi'])
        sarja['sData'] = sData
        result.append(sarja)
    result.sort(key=lambda x: x['sNimi'])

    return result

#########################################################################

@fileOpener
def getSarjatByKisaNimi(kNimi,data=None):
    sarjat = []
    for k in data:
        if kNimi == k['nimi']:
            if 'sarjat' in k:
                for s in k['sarjat']:
                    sarjat.append({'id': s['id'],
                                   'nimi':s['nimi'],
                                   'kilpailu': k['id']})
            sarjat.sort(key=lambda x: x['nimi'])
            return sarjat
    return None

#########################################################################

@fileOpener
def getSarjaByJoukkueId(jId,data=None):
    for k in data:
        if 'sarjat' in k:
            for s in k['sarjat']:
                if 'joukkueet' in s:
                    for j in s['joukkueet']:
                        if j['id'] == jId:
                            return {'id': s['id'],'nimi':s['nimi']}
    return None

#########################################################################

@fileOpener
def lisaaSarja(sarja,data=None):
    for k in data:
        if k['id'] == sarja['kilpailu']:
            if 'sarjat' not in k:
                k['sarjat'] = []
            sarja['id'] = createUniqueId('sarja')
            k['sarjat'].append(sarja)
            saveData(data)
            break

#########################################################################

@fileOpener
def poistaSarja(sarja,data=None):
    for k in data:
        if 'sarjat' in k:
            for i in range(len(k['sarjat'])):
                if k['sarjat'][i]['id'] == sarja['id']:
                    del k['sarjat'][i]
                    saveData(data)
                    break

#########################################################################

@fileOpener
def poistaRasti(rastiId,data=None):
    for k in data:
        if 'rastit' in k:
            for i in range(len(k['rastit'])):
                if k['rastit'][i]['id'] == rastiId:
                    del(k['rastit'][i])
                    saveData(data)
                    return

#########################################################################

@fileOpener
def poistaJoukkue(jNimi,data=None):
    for k in data:
        if 'sarjat' in k:
            for s in k['sarjat']:
                if 'joukkueet' in s:
                    for x in range(len(s['joukkueet'])):
                        if s['joukkueet'][x]['nimi'] == jNimi:
                            del(s['joukkueet'][x])
                            saveData(data)
                            break

#########################################################################

@fileOpener
def getSarjaByKisaNimi(kisaNimi, sarjaNimi,data=None):
    for k in data:
        if k['nimi'] == kisaNimi:
            if 'sarjat' in k:
                for s in k['sarjat']:
                    if s['nimi'] == sarjaNimi:
                        return {'id': s['id'],'nimi':s['nimi']}

#########################################################################

@fileOpener
def haeJoukkueenRastileimaukset(joukkueId,data=None):
    joukkue = None
    kisa = None
    for k in data:
        if 'sarjat' in k:
            for s in k['sarjat']:
                if 'joukkueet' in s:
                    for j in s['joukkueet']:
                        if j['id'] == joukkueId:
                            joukkue = j
                            kisa = k
                            break
    if joukkue is None:
        return []

    if 'tupa' not in kisa:
        return []

    if 'rastit' not in kisa:
        return []

    tuvat = [x for x in kisa['tupa'] if x['joukkue'] == joukkueId]
    kunnonTuvat = []
    for t in tuvat:
        try:
            kunnonTuvat.append({'rasti':int(t['rasti']),'aika':t['aika']})
        except:
            pass
    result = []

    for t in kunnonTuvat:
        rId = t['rasti']
        for r in kisa['rastit']:
            if r['id'] == rId:
                result.append({'tAika':t['aika'],'rKoodi':r['koodi']})
    result.sort(key=lambda x: x['tAika'])
    return result

#########################################################################

@fileOpener
def getRastiByKilpailuAndKoodi(kId,koodi,data=None):
    for k in data:
        if k['id'] == kId:
            if 'rastit' in k:
                for r in k['rastit']:
                    if r['koodi'] == koodi:
                        return r
    return None

#########################################################################

@fileOpener
def getTupaData(aika,koodi,jNimi,data=None):

    # Haetaan joukkueen id.
    jId = None
    try:
        jId = getJoukkueByNimi(jNimi,data=data)['id']
    except Exception as e:
        debug(u"Ei onnistuttu hakemaan joukketta {0}".format(jNimi))
        debug(e)
        return None

    # Haetaan kilpailu.
    kisa = None
    for k in data:
        if 'sarjat' in k:
            for s in k['sarjat']:
                if 'joukkueet' in s:
                    for j in s['joukkueet']:
                        if jNimi == j['nimi']:
                            kisa = k
                            break
    if kisa is None:
        return

    # Haetaan rasti.
    r = getRastiByKilpailuAndKoodi(kisa['id'],koodi)
    if r is None:
        return

    for k in data:
        if 'tupa' in k:
            for t in k['tupa']:
                if t['aika'] == aika and r['koodi'] == koodi and t['joukkue'] == jId:
                    return {'aika': t['aika'],
                            'koodi': koodi,
                            'rid': t['rasti'],
                            'jid': jId,
                            'nimi': jNimi}
          #  result.append({'aika': row['aika'],
          #                 'koodi': row['koodi'],
          #                 'rid': row['rid'],
          #                 'jid': row['jid'],
          #                 'nimi':row['joukkue']})
    return None

#########################################################################

# Jos muokkaa onnistuneesti, palautta True, muutoin False.
@fileOpener
def paivitaJoukkue(joukkue,data=None):

    last = u""
    
    # Poistetaan vanha.
    for k in data:
        if 'sarjat' in k:
            for s in k['sarjat']:
                if 'joukkueet' in s:
                    for x in range(len(s['joukkueet'])):
                            if s['joukkueet'][x]['id'] == joukkue['id']:
                                last = s['joukkueet'][x]['last']
                                del(s['joukkueet'][x])
                                break
    # Tallennetaan.
    for k in data:
        if 'sarjat' in k:
            for s in k['sarjat']:
                if s['id'] == joukkue['sarja']:
                    j = {'id':joukkue['id'],
                         'nimi': joukkue['nimi'],
                         'last': last,
                         'jasenet': json.loads(joukkue['jasenet'])}
                    s['joukkueet'].append(j)
                    break
    saveData(data)
    return True

#########################################################################

# Jos muokkaa onnistuneesti, palautta True, muutoin False.
@fileOpener
def paivitaRasti(rasti,data=None):
    poistaRasti(rasti['id'],data=data)
    tallennaRasti(rasti,data=data)

#########################################################################

@fileOpener
def getSarjat(data=None):
    sarjat = []
    for k in data:
        if 'sarjat' in k:
            for s in k['sarjat']:
                sarjat.append(s)
    return sarjat

#########################################################################

@fileOpener
def getJoukkueet(data=None):
    joukkueet = []
    for s in getSarjat(data=data):
        if 'joukkueet' in s:
            for j in s['joukkueet']:
                joukkueet.append(j)
    return joukkueet

#########################################################################

@fileOpener
def getAllRastit(data=None):
    rastit = []
    for k in data:
        if 'rastit' in k:
            for r in k['rastit']:
                rastit.append(r)
    return rastit

#########################################################################

# tags 'kilpailu' 'sarja' 'joukkue' 'rasti'}
def createUniqueId(tag):

    def createId(idt):
        newId = random.randint(0,1000000)
        while newId in idt:
            newId = random.randint(0,1000000)
        return newId

    def createKisaId():
        idt = [int(x['id']) for x in getKilpailut()]
        return createId(idt)

    def createSarjaId():
        idt = [int(x['id']) for x in getKilpailut()]
        return createId(idt)

    def createJoukkueId():
        idt = [int(x['id']) for x in getJoukkueet()]
        return createId(idt)

    def createRastiId():
        debug(u"cerateRastiId")
        idt = []
        for b in getAllRastit():
            try:
                idt.append(int(b['id']))
            except Exception as e:
                debug(e)
        return createId(idt)

    options = {'kilpailu': createKisaId,
               'sarja': createSarjaId,
               'joukkue': createJoukkueId,
               'rasti': createRastiId}

    try:
        return options[tag]()
    except Exception as e:
        debug(e)
        debug(u"Ei ole sellaista tagia {0}.".format(tag))

    return None

