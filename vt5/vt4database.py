#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys
import imp
import os
from functools import wraps
import sqlite3
import inspect
import json
from sets import Set
import logging
import hashlib

logging.basicConfig(filename=u'../../../../flaskLog/flask.log', level=logging.DEBUG)
#logging.basicConfig(filename=u'../../../flaskLog/flask.log', level=logging.DEBUG)

# Tassa on kaikki tarvittava tietokannan hakuun vt4 varten.

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

# Wrapperi funktio, joka pitaa huolen, etta tietokantayhteys avataan 
# ja suljetaan. Jos con maaritellaan alkuperaisessa funktiokutsussa, 
# ei tassa avata uutta tietokanta yhteytta. Mutta jos con on None 
# alkuperaisessa funktiokustussa, tallon luodaan tassa tietokanta yhteys.
def sqlOpener(f):
    @wraps(f)
    def wrapper(*args,**kwds):

        closeConnection = True

        con = None
        c = [v for k,v in kwds.iteritems() if k == u"con"]

        # Katsotaan loytyyko argumenttilista con.
        if len(c) == 1:
            # Poistetaan con.
            kwds.pop('con',None)
            # Otetaan data talteen con-muuttujaan.
            con = c[0]
            # Tama funktio ei saa sulkea yhteytta.
            # Sen tekee jokin tata kutsuva funktio.
            closeConnection = False

        result = None
        try:
            # Luodaan tietokanta yhteys,jos con on None.
            if con is None:
                # Maaritellaan tassa tietokannan sijainti.
                con = sqlite3.connect(os.path.abspath('../../../../sql/tietokanta'))
                #con = sqlite3.connect(os.path.abspath('../../../sql/tietokanta'))
            # Asetetaan tietokantayhteyden asetukset.
            con.row_factory = sqlite3.Row
            con.execute(u"PRAGMA foreign_keys = ON")
            try:
                # Taalla kutsutaan varsinaista tietokanta 
                # funktiota.
                result = f(con=con,*args,**kwds)
            except Exception as b:
                debug(b)
            # Tietokanta suljetaan vain, jos se on aukaistu
            # tassa funktiossa. Muussa tapauksessa jatetaan auki.
            if closeConnection:
                con.close()
        except Exception as e:
            debug(e)
        return result
    return wrapper

###############################################################################

# Ongelmalinen silloin, jos on useita eri rasteja joilla sama koodi.
# Harkitse grouppaaminen ja laskeminen id:n mukaan.
@sqlOpener
def getRastit(kId,con=None):

    sql = """SELECT r.koodi AS koodi,
                    COUNT(t.rasti) AS lkm,
                    r.lat AS lat,
                    r.lon AS lon,
                    r.id AS id
             FROM rastit r
             LEFT OUTER JOIN tupa t ON t.rasti = r.id
             WHERE r.kilpailu = ?
             GROUP BY r.koodi"""

    cur = con.cursor()
    try:
        cur.execute(sql,(kId,))
    except Exception as e:
        debug(sys.exc_info()[0])
        debug(e)
    result = []
    for row in cur.fetchall():
        result.append({'lkm': row['lkm'],
                       'koodi':row['koodi'],
                       'lon':row['lon'],
                       'id':row['id'],
                       'lat':row['lat']})
    return result

###############################################################################

# Palauttaa joukkueen nimen perusteella jos sellainen loytyy, muuten palauttaa None.
@sqlOpener
def getJoukkueByNimi(nimi,con=None):
    nimi = nimi.strip()
    sql = """SELECT * FROM joukkueet WHERE nimi = ?"""
    cur = con.cursor()
    try:
        cur.execute(sql,(nimi,))
    except Exception as e:
        debug(sys.exc_info()[0])
        debug(e)
    result = []
    for row in cur.fetchall():
        result.append({'id': row['id'],
                       'nimi':row['nimi'],
                       'sarja':row['sarja'],
                       'salasana':row['salasana'],
                       'jasenet':json.loads(row['jasenet'])})
    if len(result) > 0:
        return result[0]
    return None

###############################################################################

# Palauttaa joukkueen idn nimen perusteella jos sellainen loytyy, muuten palauttaa None.
@sqlOpener
def getJoukkueById(jId,con=None):
    sql = """SELECT * FROM joukkueet WHERE id = ?"""
    cur = con.cursor()
    try:
        cur.execute(sql,(jId,))
    except Exception as e:
        debug(sys.exc_info()[0])
        debug(e)
    result = []
    for row in cur.fetchall():
        result.append({'id': row['id'],
                       'nimi':row['nimi'],
                       'sarja':row['sarja'],
                       'salasana':row['salasana'],
                       'jasenet':json.loads(row['jasenet'])})
    if len(result) > 0:
        return result[0]
    return None

###############################################################################

@sqlOpener
def tallennaJoukkue(joukkue,con=None):
    sql = """INSERT INTO joukkueet (nimi,sarja,jasenet)
             VALUES (:nimi,:sarja,:jasenet)"""
    cur = con.cursor()
    try:
        cur.execute(sql,joukkue)
        #con.commit()
    except Exception as e:
        debug(sys.exc_info()[0])
        debug(e)
        return

    # Luodaan samantien tiea2080 salasana.
    joukkueenId = cur.lastrowid
    debug(u"öhömmm")
    debug(joukkueenId)
    debug(u"öllkjkhhömmm")

    d = hashlib.sha512()
    d.update(str(joukkueenId))
    d.update(u"tiea2080")
    uusiSalasana = d.hexdigest().decode("UTF-8")

    sql2 = """UPDATE joukkueet SET salasana = :s
             WHERE id = :id"""

    try:
        cur.execute(sql2,{'s': uusiSalasana, 'id': joukkueenId})
    except Exception as e:
        con.rollback()
        debug(sys.exc_info()[0])
        debug(e)
        return
    con.commit()

###############################################################################

@sqlOpener
def tallennaTupa(rId,jId,aika,con=None):
    debug(u"talennellaaanpi....")
    d = {'rId':rId,'jId':jId,'aika':aika}
    debug(d)
    sql = """INSERT INTO tupa (aika,rasti,joukkue)
             VALUES (:aika,:rId,:jId)"""
    cur = con.cursor()
    try:
        cur.execute(sql,d)
        con.commit()
    except Exception as e:
        debug(sys.exc_info()[0])
        debug(e)

###############################################################################

@sqlOpener
def tallennaRasti(rasti,con=None):
    sql = """INSERT INTO rastit (lat,lon,koodi,kilpailu)
             VALUES (:lat,:lon,:koodi,:kilpailu)"""
    cur = con.cursor()
    try:
        cur.execute(sql,rasti)
        con.commit()
    except Exception as e:
        debug(sys.exc_info()[0])
        debug(e)

###############################################################################

@sqlOpener
def poistaTupa(tupa,con=None):

    sql = """DELETE FROM tupa
             WHERE rasti = :rId AND joukkue = :jId AND aika = :aika"""

    cur = con.cursor()
    try:
        cur.execute(sql,tupa)
        con.commit()
    except Exception as e:
        debug(sys.exc_info()[0])
        debug(e)

###############################################################################

@sqlOpener
def muokkaaTupa(vanhaTupa,rId,jId,koodi,con=None):
    d = {'vRasti':vanhaTupa['rId'],
         'vJoukkue':vanhaTupa['jId'],
         'vAika':vanhaTupa['aika']}

    sql = """DELETE FROM tupa
             WHERE rasti = :vRasti AND joukkue = :vJoukkue AND aika =
             :vAika"""

    cur = con.cursor()
    try:
        cur.execute(sql,d)
        #con.commit()
    except Exception as e:
        debug(sys.exc_info()[0])
        debug(e)

    # Pitaisi laittaa tallennaTupa heittamaan poikkeuksen, jotta 
    # rollback toimisi parhaiten.
    try:
        debug(u"yhyy")
        tallennaTupa(rId,jId,koodi,con=con)
        debug(u"ahaa!")
        debug(rId)
        debug(jId)
        debug(koodi)
        con.commit()
    except Exception as e:
        debug(sys.exc_info()[0])
        debug(e)
        con.rollback()
    debug(u"valmnis")

###############################################################################

@sqlOpener
def getJoukkueetBySarjaId(sId,con=None):
    sql = """SELECT * FROM joukkueet j
             WHERE j.sarja IN
               (SELECT s.id FROM sarjat s
                WHERE s.id = ?)
             ORDER BY nimi"""
    cur = con.cursor()
    try:
        cur.execute(sql,(sId,))
    except Exception as e:
        debug(sys.exc_info()[0])
        debug(e)
    result = []
    for row in cur.fetchall():
        result.append({'id': row['id'],
                       'nimi':row['nimi'],
                       'sarja':row['sarja'],
                       'jasenet':json.loads(row['jasenet'])})
    return result

###############################################################################

@sqlOpener
def getKilpailu(joukkueId,con=None):
    sql = """SELECT * FROM kilpailut k
             WHERE k.id IN
               (SELECT s.kilpailu FROM sarjat s
                WHERE s.id IN
                  (SELECT j.sarja FROM joukkueet j
                   WHERE j.id == ?))"""
    cur = con.cursor()
    try:
        cur.execute(sql,(joukkueId,))
    except Exception as e:
        debug(sys.exc_info()[0])
    result = []
    for row in cur.fetchall():
        result.append({'id': row['id'],
                       'nimi':row['nimi'],
                       'alkuaika':row['alkuaika'],
                       'kesto':row['kesto'],
                       'loppuaika':row['loppuaika']})
    if len(result) > 0:
        return result[0]
    return None

###############################################################################

@sqlOpener
def getKilpailuByNimi(kilpailuNimi,con=None):
    debug(kilpailuNimi)
    sql = """SELECT * FROM kilpailut
             WHERE nimi = ?"""
    cur = con.cursor()
    try:
        cur.execute(sql,(kilpailuNimi,))
    except Exception as e:
        debug(sys.exc_info()[0])
    result = []
    for row in cur.fetchall():
        result.append({'id': row['id'],
                       'nimi':row['nimi'],
                       'alkuaika':row['alkuaika'],
                       'kesto':row['kesto'],
                       'loppuaika':row['loppuaika']})
    if len(result) > 0:
        return result[0]
    return None

###############################################################################

@sqlOpener
def getKilpailut(con=None):
    sql = """SELECT * FROM kilpailut"""
    cur = con.cursor()
    try:
        cur.execute(sql)
    except Exception as e:
        debug(sys.exc_info()[0])
        debug(e)
    result = []
    for row in cur.fetchall():
        result.append({'id': row['id'],
                       'nimi':row['nimi'],
                       'alkuaika':row['alkuaika'],
                       'kesto':row['kesto'],
                       'loppuaika':row['loppuaika']})
    return result

###############################################################################

# TODO: testaa mita kay jos on ainoastaan joukkue ilman jasenia.
@sqlOpener
def getDataToJoukkuelistaus(kilpailunNimi,con=None):

    sql = """SELECT s.nimi AS sNimi, j.nimi AS jNimi, j.jasenet 
             FROM kilpailut k
             LEFT OUTER JOIN sarjat s ON s.kilpailu == k.id
             LEFT OUTER JOIN joukkueet j ON j.sarja == s.id
             WHERE k.nimi == ?
             ORDER BY snimi, jNimi"""

    cur = con.cursor()
    try:
        cur.execute(sql,(kilpailunNimi,))
    except Exception as e:
        debug(sys.exc_info()[0])
    result = []
    try:
        for row in cur.fetchall():
            result.append({'sNimi': row['sNimi'],
                           'jNimi':row['jNimi'],
                           'jasenet':sorted(json.loads(row['jasenet']))})
    except Exception as e:
        debug(e)
    finalResult = {}
    for x in result:
        finalResult.setdefault(x['sNimi'],[]).append({'jNimi':x['jNimi'],'jasenet':x['jasenet']})
    return sorted([{'sNimi':k, 'sData':v} for k,v in finalResult.iteritems()],key=lambda x:x['sNimi'])

###############################################################################

@sqlOpener
def getSarjatByKisaNimi(kNimi,con=None):

    sql = """SELECT *
             FROM sarjat s
             WHERE s.kilpailu IN
               (SELECT k.id
                FROM kilpailut k
                WHERE k.nimi == ?)
             ORDER BY nimi"""

    cur = con.cursor()
    try:
        cur.execute(sql,(kNimi,))
    except Exception as e:
        debug(sys.exc_info()[0])
    result = []
    try:
        for row in cur.fetchall():
            result.append({'id': row['id'],
                           'nimi':row['nimi'],
                           'matka':row['matka'],
                           'alkuaika': row['alkuaika'],
                           'loppuaika': row['loppuaika'],
                           'kesto': row['kesto'],
                           'kilpailu': row['kilpailu']})
    except Exception as e:
        debug(e)
    return result

###############################################################################

@sqlOpener
def getSarjaByJoukkueId(jId,con=None):

    sql = """SELECT *
             FROM sarjat s
             WHERE s.id IN
               (SELECT j.sarja
                FROM joukkueet j
                WHERE j.id == ?)"""

    cur = con.cursor()
    try:
        cur.execute(sql,(jId,))
    except Exception as e:
        debug(sys.exc_info()[0])
        debug(e)
    result = []
    try:
        for row in cur.fetchall():
            result.append({'id': row['id'],
                           'nimi':row['nimi'],
                           'matka':row['matka'],
                           'alkuaika': row['alkuaika'],
                           'loppuaika': row['loppuaika'],
                           'kesto': row['kesto'],
                           'kilpailu': row['kilpailu']})
    except Exception as e:
        debug(e)
    if len(result) == 1:
        return result[0]
    return None

###############################################################################

@sqlOpener
def lisaaSarja(sarja,con=None):
    debug(sarja)
    sql = """INSERT INTO sarjat (nimi, matka, alkuaika, loppuaika, kesto, kilpailu)
             VALUES (:nimi, :matka, :alkuaika, :loppuaika, :kesto, :kilpailu)
             """
    cur = con.cursor()
    try:
        cur.execute(sql,sarja)
        con.commit()
    except Exception as e:
        debug(sys.exc_info()[0])
        debug(e)

###############################################################################

@sqlOpener
def poistaSarja(sarja,con=None):
    sql = """DELETE FROM sarjat
             WHERE id = :id"""
    cur = con.cursor()
    try:
        cur.execute(sql,sarja)
        con.commit()
    except Exception as e:
        debug(sys.exc_info()[0])
        debug(e)

###############################################################################

@sqlOpener
def poistaRasti(rastiId,con=None):
    debug(u"poistetaan")
    sql = """DELETE FROM rastit
             WHERE id = ?"""
    cur = con.cursor()
    try:
        cur.execute(sql,(rastiId,))
        con.commit()
    except Exception as e:
        debug(sys.exc_info()[0])
        debug(e)

###############################################################################

@sqlOpener
def poistaJoukkue(jNimi,con=None):
    sql = """DELETE FROM joukkueet
             WHERE nimi = ?"""
    cur = con.cursor()
    try:
        cur.execute(sql,(jNimi,))
        con.commit()
    except Exception as e:
        debug(sys.exc_info()[0])
        debug(e)

###############################################################################

@sqlOpener
def getSarjaByKisaNimi(kisaNimi, sarjaNimi,con=None):

    conds = {'kNimi': kisaNimi, 'sNimi': sarjaNimi}

    sql = """SELECT *
             FROM sarjat s
             WHERE s.kilpailu IN
               (SELECT k.id
                FROM kilpailut k
                WHERE k.nimi == :kNimi)
             AND s.nimi = :sNimi"""

    cur = con.cursor()
    try:
        cur.execute(sql,conds)
    except Exception as e:
        debug(sys.exc_info()[0])
    result = []
    try:
        for row in cur.fetchall():
            result.append({'id': row['id'],
                           'nimi':row['nimi'],
                           'matka':row['matka'],
                           'alkuaika': row['alkuaika'],
                           'loppuaika': row['loppuaika'],
                           'kesto': row['kesto'],
                           'kilpailu': row['kilpailu']})
    except Exception as e:
        debug(e)
    if len(result) == 1:
        return result[0]
    return None

###############################################################################

@sqlOpener
def haeJoukkueenRastileimaukset(joukkueId,con=None):

    sql = """SELECT t.aika AS tAika, r.koodi AS rKoodi 
             FROM tupa t
             LEFT OUTER JOIN rastit r ON r.id == t.rasti 
             LEFT OUTER JOIN joukkueet j ON j.id == t.joukkue
             WHERE j.id == ?"""

    cur = con.cursor()
    try:
        cur.execute(sql,(joukkueId,))
    except Exception as e:
        debug(sys.exc_info()[0])
        debug(e)
    result = []
    try:
        for row in cur.fetchall():
            result.append({'tAika': row['tAika'],
                           'rKoodi':row['rKoodi']})
    except Exception as e:
        debug(e)
    result.sort(key=lambda x: x['tAika'])
    return result

###############################################################################

@sqlOpener
def getRastiByKilpailuAndKoodi(kId,koodi,con=None):
    d = {'kId': kId, 'koodi': koodi}

    sql = """SELECT r.koodi AS koodi,
                    r.lat AS lat,
                    r.lon AS lon,
                    r.id AS id,
                    r.kilpailu AS kilpailu
             FROM rastit r
             WHERE r.kilpailu IN
               (SELECT k.id FROM kilpailut k
                WHERE k.id = :kId)
             AND r.koodi = :koodi"""

    cur = con.cursor()
    try:
        cur.execute(sql,d)
    except Exception as e:
        debug(sys.exc_info()[0])
        debug(e)
    result = []
    for row in cur.fetchall():
        result.append({'koodi':row['koodi'],
                       'lon':row['lon'],
                       'id':row['id'],
                       'lat':row['lat'],
                       'kilpailu': row['kilpailu']})
    if len(result) > 0:
        return result[0]
    return None

###############################################################################

@sqlOpener
def getTupaData(aika,koodi,jNimi,con=None):
    d = {'aika': aika, 'koodi': koodi, 'jNimi': jNimi}

    sql = """SELECT r.id AS rid, j.id AS jid, t.aika AS aika, r.koodi AS koodi, j.nimi AS joukkue
             FROM tupa t
             LEFT OUTER JOIN rastit r ON r.id = t.rasti
             LEFT OUTER JOIN joukkueet j ON j.id = t.joukkue
             WHERE t.aika = :aika AND r.koodi = :koodi AND j.nimi = :jNimi"""

    cur = con.cursor()
    try:
        cur.execute(sql,d)
    except Exception as e:
        debug(sys.exc_info()[0])
        debug(e)
    result = [] 
    try:
        for row in cur.fetchall():
            result.append({'aika': row['aika'],
                           'koodi': row['koodi'],
                           'rid': row['rid'],
                           'jid': row['jid'],
                           'nimi':row['joukkue']})
    except Exception as e:
        debug(e)
    if len(result) > 0:
        return result[0]
    return None


###############################################################################

# Jos muokkaa onnistuneesti, palautta True, muutoin False.
@sqlOpener
def paivitaJoukkue(joukkue,con=None):
    if joukkue is None:
        debug(u"Ei voida tallentaa. Joukkue == None.")
        return False

    variables = None
    try:
        variables = {'jId': joukkue['id'], 'jSarja': joukkue['sarja'], 'jNimi': joukkue['nimi'], 'jJasenet': joukkue['jasenet'], 'salasana':joukkue['salasana']}
        debug(variables)
    except Exception as e:
        debug(e)
        return False

    sql = """UPDATE joukkueet 
             SET nimi = :jNimi, sarja = :jSarja, jasenet = :jJasenet, salasana
             = :salasana
             WHERE id = :jId"""

    cur = con.cursor()
    try:
        cur.execute(sql,variables)
        con.commit()
    except Exception as e:
        debug(sys.exc_info()[0])
        debug(e)
        return False
    return True

###############################################################################

# Jos muokkaa onnistuneesti, palautta True, muutoin False.
@sqlOpener
def paivitaRasti(rasti,con=None):

    sql = """UPDATE rastit
             SET lat = :lat, lon = :lon, koodi = :koodi 
             WHERE id = :id"""

    cur = con.cursor()
    try:
        cur.execute(sql,rasti)
        con.commit()
    except Exception as e:
        debug(sys.exc_info()[0])
        debug(e)

###############################################################################

@sqlOpener
def checkPasswordVT5(salasana, jNimi,con=None):
    sql = """SELECT id, salasana
             FROM joukkueet
             WHERE nimi = ?"""

    cur = con.cursor()
    try:
        cur.execute(sql,(jNimi,))
    except Exception as e:
        debug(sys.exc_info()[0])
        debug(e)
        return False

    result = []
    haettuDigest = u""

    try:
        for row in cur.fetchall():
            result.append({'salasana': row['salasana'], 'id': row['id']})
    except Exception as e:
        debug(e)
        return False

    if len(result) != 1:
        return False

    haettuDigest = result[0]['salasana']

    # Luodaan digest kayttajan antamasta salasanasta.
    token = hashlib.sha512()
    token.update(str(result[0]['id']))
    token.update(salasana)
    digest = token.hexdigest()
    return digest == haettuDigest

#########################################################################

def checkAdminPasswordVT4(pwd):
    token = hashlib.sha512()
    token.update("erkkiajaamopolla")
    token.update(pwd)
    digest = "EY\x9d\xc5\x9f\xa1\x91\xbd\x90\xcfEu\xe8\x84,\xa5\x9a\xf6:\xa2\x11>\xee\xe2\xf6\x9c\xa1\xf2>\xeaK\x9dQF\x82\xcc\xbap\xf8A\x13\xe3\xb2lF\xcc\x9cG\xd3\xce\xabq,e\xe6\xff\xb0\x80\x14\x9e\xc7U>\xa0"
    return token.digest() == digest

###############################################################################
