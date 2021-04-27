# -*- coding: utf-8 -*-

from flask import Flask, render_template, request, make_response, redirect, url_for
import json
from google.appengine.ext import ndb
from wtforms_appengine.ndb import model_form
from wtforms_appengine.fields import KeyPropertyField
from flask_wtf import FlaskForm
from wtforms import SelectField, HiddenField, StringField, ValidationError
from wtforms.validators import InputRequired
from wtforms import validators
from datetime import datetime
from luokat import *

#########################
### Tietokantajutut   ###
#########################

####################################################################################################

# Etsii tietokannasta kilpailun id:n perusteella.
def getKilpailu(kilpailu_id):
    try:
        return ndb.Key(urlsafe=kilpailu_id).get()
    except:
        print u"Ei loytynyt kilpailua " + kilpailu_id

####################################################################################################

# Etsii tietokannasta kilpailun joukkueen perusteella.
def getKilpailuByJoukkue(joukkue_obj):
    sarja = getSarja(joukkue_obj.sarja.urlsafe())
    return getKilpailu(sarja.kilpailu.urlsafe())

####################################################################################################

# Paivittaa kilpailun annetusta kilpailuFormista. 
# Asettaa kilpailuFormiin mahdolliset virheet.
# Luottaa siihen etta lomakkeen validoinnit ovat suoritettu.
def updateKilpailu(kilpailu_id, kilpailuForm):
    print u"updatetetaan kilailua"

    kilpailu = None

    # Jos ollaan muokkaamassa olemassa olevaa joukkuetta. 
    if (kilpailu_id != '0'):
        kilpailu = getKilpailu(kilpailu_id)
        assert kilpailu is not None, u"updateKilpailu: Kilpailua " + kilpailu_id + " ei loydy."

    # Tarkistetaan onko nimi jo kaytossa.
    try:
        if not tarkistaKilpailuNimi(kilpailu_id, kilpailuForm.nimi.data.strip()):
            kilpailuForm.nimi.errors.append(u"Kilpailun nimi on jo käytossa.")
            raise Exception(u'Kilpailun nimi on kaytossa.')
    except Exception as e:
        print e.message.encode("utf-8")
        raise Exception(u"Kilpailun nimi on jo kaytossa.")

    # Asetetaan kilpailut propertyt kohdilleen.

    if kilpailu is None:
        kilpailu = Kilpailu()

    try:
        kilpailu.nimi = kilpailuForm.nimi.data.strip()
    except Exception as e:
        raise AssertionError(u"updateKilpailu: kilpailu.nimi epannoistui.'" + unicode(e) + "'.")
    try:
        kilpailu.alkuaika = datetime.strptime(kilpailuForm.alkuaika.data.strip(), "%Y-%m-%d %H:%M:%S")
    except Exception as e:
        raise AssertionError(u"updateKilpailu: kilpailu.alkuaika epannoistui.'" + unicode(e) + "'.")
    try:
        kilpailu.loppuaika = datetime.strptime(kilpailuForm.loppuaika.data.strip(), "%Y-%m-%d %H:%M:%S")
    except Exception as e:
        raise AssertionError(u"updateKilpailu: kilpailu.loppuaika epannoistui.'" + unicode(e) + "'.")
    try:
        kilpailu.kesto = int(kilpailuForm.kesto.data.strip())
    except:
        raise AssertionError(u"updateKilpailu: kilpailu.kesto epannoistui. '" + kilpailuForm.kesto.data.strip() + "'.")

    # Yritetaan paivittaa kilpailua. Tehdaan put metodin yhteydessa 
    # viela alkua-aika/loppu-aika tarkistus.
    try:
        print u"tallennetaan kilpailua"
        return kilpailu.put()
    except ValueError as e:
        kilpailuForm.alkuaika.errors.append(unicode(e))
        raise Exception(unicode(e))


####################################################################################################

# Paivittaa sarjat annetusta sarjaFormista. 
# Asettaa formiin mahdolliset virheet.
# Luottaa siihen etta lomakkeen validoinnit ovat suoritettu.
def updateSarja(kilpailu_id, sarja_id, sarjaForm):

    print u"updateSarja"
    sarja = None

    # Jos ollaan muokkaamassa olemassa olevaa sarjaa. 
    if (sarja_id != '0'):
        sarja = getSarja(sarja_id)
        assert sarja is not None, u"updateSarja: Sarjaa " + sarja_id + " ei loydy."

    # Tarkistetaan onko sarjan nimi jo kaytossa samassa kilpailussa.
    if not tarkistaSarjaNimi(kilpailu_id, sarja_id, sarjaForm.nimi.data.strip()):
        sarjaForm.nimi.errors.append(u"Sarjan nimi on jo kaytossa.")
        raise Exception(u'updateSarja: Sarjan nimi on kaytossa.')

    # Asetetaan sarjan propertyt kohdilleen.
    print u"luodaan sarja"

    if sarja is None:
        sarja = Sarja()

    try:
        sarja.nimi = sarjaForm.nimi.data.strip()
    except Exception as e:
        raise AssertionError(u"updateSarja: sarja.nimi epannoistui.'" + str(e) + "'.")
    try:
        sarja.kesto = int(sarjaForm.kesto.data.strip())
    except:
        raise AssertionError(u"updateSarja: sarja.kesto epannoistui. '" + sarjaForm.kesto.data.strip() + "'.")
    print u"sarja luotu/muokattu"

    # yritetaan paivittaa sarja. viela alkua-aika/loppu-aika tarkistus.
    try:
        kilpailu = getKilpailu(kilpailu_id)
        sarja.kilpailu = kilpailu.key
        return sarja.put()
    except ValueError as e:
        raise Exception(unicode(e))

    print u"end of updateSarja"

####################################################################################################

# Paivittaa joukkueen annetusta joukkueFormista. 
# Asettaa formiin mahdolliset virheet.
# Luottaa siihen etta lomakkeen validoinnit ovat suoritettu.
def updateJoukkue(kilpailu_id, sarja_id, joukkue_id, joukkueForm,max_len):

    print u"updateJoukkue"
    joukkue = None

    # Jos ollaan muokkaamassa olemassa olevaa joukkuetta. 
    if (joukkue_id != '0'):
        joukkue = getJoukkue(joukkue_id)
        assert joukkue is not None, u"updatejoukkue: joukkuetta " + joukkue_id + " ei loydy."

    # Asetetaan sarjan propertyt kohdilleen.
    print u"luodaan joukkue"

    if joukkue is None:
        joukkue = Joukkue()

    # Tsekataan sarja.
    try:
        sarja = getSarjaByNimi(kilpailu_id,joukkueForm.sarja.data.strip())
        if len(sarja) == 0:
            raise Exception(u"Sarjan nimeä ei löytynyt annetusta kilpailusta.")
        joukkue.sarja = sarja[0].key
    except Exception as e:
        raise AssertionError(u"updateJoukkue: joukkue.sarja epannoistui. '" + joukkueForm.sarja.data.strip() + "'. " + unicode(e))

    # Tsekataan joukkueen nimi.
    joukkue.nimi = joukkueForm.nimi.data.strip()

    ## tsekkaa onko nyt tassa kilpailussa jo saman niminen joukkue
    print joukkue.nimi
    print joukkue.sarja
    if not tarkistaJoukkueNimi(kilpailu_id, joukkue_id, joukkue.nimi):
        message = u"Saman niminen joukkue on jo kisassa."
        joukkueForm.nimi.errors.append(message)
        raise Exception(message)

    try:
        jasenet = []
        for i in range(max_len):
            name = u"jasen" + unicode(i)
            jasen = joukkueForm[name].data.strip()
            if len(jasen) != 0:
                jasenet.append(jasen)
        joukkue.jasenet = jasenet
        if len(jasenet) < 2:
            raise Exception(u"Joukkueita täytyy olla vähintään kaksi")
    except Exception as e:
        joukkueForm.jasen0.errors.append(unicode(e))
        raise Exception(u"updateJoukkue: joukkue.jasenet epannoistui. '" + unicode(e) + u"'.")

    print u"joukkue luotu/muokattu"

    # Yritetaan paivittaa joukkuetta. Tehdaan put metodin yhteydessa 
    # viela lopputarkistus.
    try:
        return joukkue.put()
    except Exception as e:
        raise Exception(unicode(e))

    print u"end of updateJoukkue"

####################################################################################################

# Paivittaa rastin annetusta sarjaFormista. 
# Asettaa formiin mahdolliset virheet.
# Luottaa siihen etta lomakkeen validoinnit ovat suoritettu.
def updateRasti(kilpailu_id, rasti_id, rastiForm):

    print u"updateRasti"
    rasti = None

    # Jos ollaan muokkaamassa olemassa olevaa rastia. 
    if (rasti_id != '0'):
        rasti = getRasti(rasti_id)
        assert rasti is not None, u"updateRasti: Rastia " + rasti_id + " ei loydy."

    # Tarkistetaan onko rastin nimi jo kaytossa samassa kilpailussa.
    if not tarkistaRastiKoodi(kilpailu_id, rasti_id, rastiForm.koodi.data.strip()):
        rastiForm.koodi.errors.append(u"Rastin nimi on jo kaytossa tässä kilpailussa.")
        raise Exception(u'updateRasti: Rastin nimi on kaytossa.')

    # Asetetaan rastin propertyt kohdilleen.
    print u"luodaan rasti"

    if rasti is None:
        rasti = Rasti()

    try:
        rasti.koodi = rastiForm.koodi.data.strip()
    except Exception as e:
        raise AssertionError(u"updateRasti: sarja.rasti epannoistui.'" + unicode(e) + "'.")
    try:
        rasti.lat = rastiForm.lat.data
    except Exception as e:
        raise AssertionError(u"updateRasti: rasti.lat epannoistui. " + unicode(e))
    try:
        rasti.lon = rastiForm.lon.data
    except Exception as e:
        raise AssertionError(u"updateRasti: rasti.lon epannoistui. " + unicode(e))
    print u"rasti luotu/muokattu"

    # yritetaan paivittaa rasti.
    try:
        kilpailu = getKilpailu(kilpailu_id)
        rasti.kilpailu = kilpailu.key
        return rasti.put()
    except ValueError as e:
        raise Exception(unicode(e))

    print u"end of updateSarja"

####################################################################################################

# Tarkistaa onko kilpailu_id:n omaavalla kilpailulla uniikki nimi.
# Palauttaa True jos kilpailun nimea ei ole jollakin muulla joukkueella.
# Muussa tapausessa palauttaa False.
def tarkistaKilpailuNimi(kilpailu_id, kilpailu_nimi):
    print u"tyyppi::"
    print type(kilpailu_nimi)
    #print kilpailu_nimi.encode("UTF-8")
#    kilpailu_nimi = kilpailu_nimi.encode('utf-8') #.encode("utf-8")
    try:
        key = ndb.Key(urlsafe=kilpailu_id)

    except Exception as e:
        #print u"TarkistaKilpailunNimi(" + kilpailu_id + u"," + unicode(kilpailu_nimi) + u"."
        #print u"Ei loytynyt kilpailua '" + kilpailu_id + u"'."
        return len(Kilpailu.query(Kilpailu.nimi == kilpailu_nimi).fetch()) == 0
#    try:
#        print u"joopajoo1"
#        joopjaoo = Kilpailu.query(ndb.AND(Kilpailu.key != key, Kilpailu.nimi == kilpailu_nimi)).fetch()
#        print u"joopajoo2"
#    except Exception as ex:
#        pass
#        #print ex.message.encode('utf-8')
#        #print unicode(ex)
    return len(Kilpailu.query(ndb.AND(Kilpailu.key != key, Kilpailu.nimi == kilpailu_nimi)).fetch()) == 0

####################################################################################################

# Tarkistaa onko kilpailu_id omaavalla kilpailulla sarjan_nimea entuudestaan. 
# Palauttaa True jos kilpailun nimea ei ole jollakin muulla sarjalla.
# Muussa tapausessa palauttaa False.
def tarkistaSarjaNimi(kilpailu_id, sarja_key, sarjan_nimi):
    kilpailu = getKilpailu(kilpailu_id)
    if kilpailu is None:
        raise AssertionError(u"Kilpailua " + unicode(kilpailu_id) + " ei löydy.")
    sarja = getSarja(sarja_key)
    if sarja is None:
        return len(Sarja.query(ndb.AND(Sarja.kilpailu == kilpailu.key,
            Sarja.nimi == sarjan_nimi)).fetch()) == 0
    else:
        return len(Sarja.query(ndb.AND(ndb.AND(Sarja.kilpailu == kilpailu.key,Sarja.key != sarja.key), Sarja.nimi == sarjan_nimi)).fetch()) == 0

####################################################################################################

# Tarkistaa onko rastin koodi jo kaytossa ko. kilpailussa. 
# Palauttaa True jos koodia nimea ei ole jollakin muulla kilpailun rastilla.
# Muussa tapausessa palauttaa False.
def tarkistaRastiKoodi(kilpailu_id, rasti_key, koodi):
    kilpailu = getKilpailu(kilpailu_id)
    if kilpailu is None:
        raise AssertionError(u"Kilpailua " + unicode(kilpailu_id) + " ei löydy.")
    rasti = getRasti(rasti_key)
    if rasti is None:
        return len(Rasti.query(ndb.AND(Rasti.kilpailu == kilpailu.key,
            Rasti.koodi == koodi)).fetch()) == 0
    else:
        return len(Rasti.query(ndb.AND(ndb.AND(Rasti.kilpailu == kilpailu.key,Rasti.key != rasti.key), Rasti.koodi == koodi)).fetch()) == 0

####################################################################################################

# Tarkistaa onko kilpailu_id omaavalla kilpailulla sarjan_nimea entuudestaan. 
# Palauttaa True jos sarjan nimea ei ole jollakin muulla joukkueella.
# Muussa tapausessa palauttaa False.
def tarkistaJoukkueNimi(kilpailu_id, joukkue_id, joukkue_nimi):
    kilpailu = getKilpailu(kilpailu_id)
    if kilpailu is None:
        raise AssertionError(u"Kilpailua " + unicode(kilpailu_id) + " ei löydy.")

    # Haetaan kilpailun sarjat.
    sarjat = getSarjat(kilpailu_id)

    # Haetaan ko. joukkue olio.
    joukkue = getJoukkue(joukkue_id)

    # Laskuri laskee muun kuin taman joukkueen nimet jotka ovat samat kuin
    # @joukkue_nimi.
    result = 0

    for s in sarjat:
        # Joukkue on uusi. Tarvitsee vain loytaa yksikin olemassa oleva
        # joukkueen nimi joka on sama kuin tassa.
        if joukkue is None:
            result += len(Joukkue.query(ndb.AND(Joukkue.sarja == s.key, joukkue_nimi == Joukkue.nimi)).fetch())
        # Joukkue on jo olemassa. Muuten sama kuin edella mutta ei lasketa
        # taman joukkueen nimea.
        else:
            result += len(Joukkue.query(
                ndb.AND(
                    ndb.AND(Joukkue.sarja == s.key,joukkue_nimi == Joukkue.nimi),
                    Joukkue.key != joukkue.key)).fetch())
    return result == 0

####################################################################################################

# Poistaa kilpailun, sen sarjat ja joukkueet TODO: poista rastit. Onnistuessaan palauttaa True. Muutoin False.
def delete_kilpailu(kilpailu_id):
    try:
        sarjat = getSarjat(kilpailu_id)
        joukkueet = []
        for s in sarjat:
            joukkue = []
            try:
                joukkue = [x for x in getJoukkueet(s.key.urlsafe())]
            except Exception as ex:
                print ex.message.encode("utf-8")
            for j in joukkue:
                joukkueet.append(j.key)
            s.key.delete()
        ndb.delete_multi(joukkueet)
        getKilpailu(kilpailu_id).key.delete()
        return True
    except Exception as e:
        print e.message.encode("utf-8")
        return False

####################################################################################################

# Poistaa sarjan ja sen joukkueet (TODO: poista rastit). Onnistuessaan palauttaa True. Muutoin False.
def delete_sarja(sarja_id):
    try:
        sarja = getSarja(sarja_id)
        joukkueet = []
        try:
            joukkue = [x for x in getJoukkueet(sarja.key.urlsafe())]
        except Exception as ex:
            print ex.message.encode("utf-8")
        for j in joukkue:
            joukkueet.append(j.key)
        sarja.key.delete()
        ndb.delete_multi(joukkueet)
        return True
    except Exception as e:
        print e.message.encode("utf-8")
        return False

####################################################################################################

# Poistaa joukkueen. Onnistuessaan palauttaa True. Muutoin False.
def delete_joukkue(joukkue_id):
    try:
        joukkue = getJoukkue(joukkue_id)
        rastit = []
#        try:
#            joukkue = [x for x in getJoukkueet(sarja.key.urlsafe())]
#        except Exception as ex:
#            unicode(ex)
#        for j in joukkue:
#            joukkueet.append(j.key)
#        sarja.key.delete()
#        ndb.delete_multi(joukkueet)
        joukkue.key.delete()
        return True
    except Exception as e:
        print e.message.encode("utf-8")
        return False

####################################################################################################

# Poistaa kilpailun rastin id:n perusteella. Poistaa myos joukkueista ne
# rastileimaukset jotka liittyvat tahan poistettavaan rastiin.
# Onnistuessaan palauttaa True. Muutoin False.
def delete_rasti(rasti_id):
    try:
        rasti = getRasti(rasti_id)
        rasti_safe = rasti.key.urlsafe()
        joukkueet = Joukkue.query().fetch()
        for j in joukkueet:

            # Laitetaan talteen ne indeksin paikat jossa esiintyy tuhottava
            # rasti.
            indices = []
            if j.rastileimaukset is None:
                j.rastileimaukset = []
            for k in range(len(j.rastileimaukset)):
                if j.rastileimaukset[k]['rasti'] == rasti_safe:
                    indices.append(k)
            if len(indices) == 0:
                continue
            print indices
            for i in range(len(indices))[::-1]:
                del j.rastileimaukset[indices[i]]
            j.put()
        rasti.key.delete()
        return True
    except Exception as e:
        print e.message.encode("utf-8")
        return False

####################################################################################################

# Etsii tietokannasta sarjan id:n perusteella.
def getSarja(sarja_id):
    try:
        return ndb.Key(urlsafe=sarja_id).get()
    except:
        print u"Ei loytynyt sarjaa " + sarja_id

####################################################################################################

# Etsii tietokannasta sarja-olion sarjan nimen ja kilpailun id:n perusteella.
def getSarjaByNimi(kilpailu_id,sarja_nimi):
    try:
        return Sarja.query(ndb.AND(Sarja.kilpailu ==
            ndb.Key(urlsafe=kilpailu_id),Sarja.nimi == sarja_nimi)).fetch()
    except:
        print u"getSarjaByNimi: Ei loytynyt sarjaa " + sarja_id + " kisasta " + kilpailu_id

####################################################################################################

# Etsii tietokannasta kaikki kilpailun sarjat.
def getSarjat(kilpailu_id):
    kilpailu = getKilpailu(kilpailu_id)
    if kilpailu is None:
        return []
    return Sarja.query(Sarja.kilpailu == kilpailu.key).order(Sarja.nimi).fetch()

####################################################################################################

# Etsii tietokannasta kaikki sarjan joukkueet.
def getJoukkueet(sarja_id):
    sarja = getSarja(sarja_id)
    if sarja is None:
        print u"No mutta sarjahan on None!!!"
        return []
    return Joukkue.query(Joukkue.sarja == sarja.key).order(Joukkue.nimi).fetch() #fetch()

####################################################################################################

# Etsii tietokannasta joukkueen id:n perusteella.
def getJoukkue(joukkue_id):
    try:
        return ndb.Key(urlsafe=joukkue_id).get()
    except:
        print u"Ei loytynyt joukkuetta " + joukkue_id

####################################################################################################

# Etsii tietokannasta kilpailun rastit id:n perusteella.
def getRastit(kilpailu_id):
    try:
        kID = ndb.Key(urlsafe=kilpailu_id)
        return Rasti.query(Rasti.kilpailu == kID).order(Rasti.koodi).fetch()
    except Exception as e:
        print u"getRastit: Ei loytynyt kilpailua. " + unicode(e)
        return []

####################################################################################################

# Etsii tietokannasta kilpailun rastit id:n perusteella.
def getRastitQuery(kilpailu_id):
    try:
        kID = ndb.Key(urlsafe=kilpailu_id)
        return Rasti.query(Rasti.kilpailu == kID).order(Rasti.koodi)
    except Exception as e:
        print u"getRastit: Ei loytynyt kilpailua. " + unicode(e)
        return None

####################################################################################################

# Etsii tietokannasta rastis rastin id:n perusteella.
def getRasti(rasti_id):
    try:
        return ndb.Key(urlsafe=rasti_id).get()
    except Exception as e:
        print u"getRasti: " + unicode(e)

####################################################################################################

def getRastiByKoodi(kilpailu_id,koodi):
    print u"getRastitByKoodi:"
    print kilpailu_id
    print koodi
    print type(koodi)

    try:
        kID = ndb.Key(urlsafe=kilpailu_id)
        return Rasti.query(ndb.AND(Rasti.kilpailu == kID, Rasti.koodi == koodi)).fetch()
    except Exception as e:
        print u"getRastitByKoodi: Ei loytynyt kilpailua. " + unicode(e)
        return None

####################################################################################################

# Poistaa joukkuuen id:n ja rastileimauksen position perusteella. Onnistuessaan palauttaa True. Muutoin False.
def delete_rastileimaus(joukkue_id, rastileimaus_id):
    try:
        joukkue = getJoukkue(joukkue_id)
        rId = int(rastileimaus_id)
        del joukkue.rastileimaukset[rId]
        joukkue.put()
        return True
    except Exception as e:
        print u"delete_rastileimaus:"
        print e.message.encode("utf-8")
        return False

####################################################################################################
