#!/usr/bin/python
# -*- coding: utf-8 -*-

from flask import Flask, g, session, redirect, url_for, escape, request, Response, render_template
import os
import sys
import hashlib
import json
import logging
from functools import wraps
import inspect
import urllib
import random
import sqlite3
import vt4database as db
import myWeb as m
import copy
from datetime import datetime

logging.basicConfig(filename=u'../../../../flaskLog/flask.log', level=logging.DEBUG)

app = Flask(__name__)
app.secret_key = u'\xf9%\xf8\xd2V+[\x1b\xfd\xac\xa6\xe9\x7f\xffmEO}\x1fgd\x1c\xfbm'

#########################################################################

def auth(f):
    ''' Tämä decorator hoitaa kirjautumisen tarkistamisen ja ohjaa
        tarvittaessa kirjautumissivulle'''
    @wraps(f)
    def decorated(*args, **kwargs):
        if not 'kirjautunut' in session:
            return redirect(url_for(u'kirjaudu'))
        return f(*args, **kwargs)
    return decorated

#########################################################################

def authAdmin(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'kirjautunut' not in session or session['kirjautunut'] != u"admin":
            return redirect(url_for(u'kirjaudu'))
        return f(*args, **kwargs)
    return decorated

#########################################################################

# Oma debuggausta helpottava apufunktio.
def debug(errorMsg):
    logging.debug(u"{0} : {1}".format(inspect.stack()[1][3], errorMsg))

#########################################################################

@app.route(u'/kirjaudu', methods=[u'POST', u'GET'])
def kirjaudu():

    salasana = u""

    # Alustetaan kirjautumisTunnus.
    if u'tempNimi' not in session:
        session['tempNimi'] = u""
    if u"adminKilpailu" not in session:
        session['adminKilpailu'] = None

    # SIvuun liittyvat muuttujat. Nama ovat nyt dictin sisalla, jotta 
    # niita voi muokata jatkossa sisafunktion kautta jos on tarve.
    pageVariables = {'errorTunnus': u"", 'errorSalasana': u"", 'salasana': u""}

    kilpailut = []

    try:
        kilpailut = [x['nimi'] for x in db.getKilpailut()]
    except Exception as e:
        debug(e)


    def updatePage():
        return render_template(u"kirjaudu.html",
                variables=pageVariables,
                kilpailut=kilpailut)

    # Jos tullaan GET-metodilla, niin piirretaan vain.
    if request.method == 'GET':
        return updatePage()

    # Jos tullaan POST:illa....
    elif request.method == 'POST':
        try:
            session['tempNimi'] = request.form['tunnus']
            session['adminKilpailu'] = db.getKilpailuByNimi(request.form.get('alasveto'))
            session['adminKilpailu']['rastitUrl'] = m.buildQuery(url_for(u"rastilistaus"),{'kNimi': session['adminKilpailu']['nimi']})
        except Exception as e:
            debug(e)
            session['tempNimi'] = u""
        try:
            salasana = request.form.get('salasana',u"")
        except Exception as e:
            debug(e)

    # Tehdaan tarkistukset.
    stripattuNimi = session['tempNimi'].strip()
    joukkue = db.getJoukkueByNimi(stripattuNimi)

    if len(stripattuNimi) == 0:
        pageVariables['errorTunnus'] = u"Nimi ei voi koostua tyhjista merkeista."
    elif session['tempNimi'] == u"admin":
        pass
    else:
        if joukkue is None:
            pageVariables['errorTunnus'] = u"Joukkuetta ei loydy."
    if len(pageVariables['errorTunnus']) > 0:
        return updatePage()

    # Ei virheita joukkuen nimen suhteen.
    # Tarkistetaan salasana.
    if stripattuNimi != u'admin' and joukkue is None:
        debug("VIRHE: joukkue ei saa olla tassa vaiheessa None!")
    # Tarkistetaan tavallisen kayttajan salasana.
    # Jos ok, niin mennaan joukkuelistaussivulle. 
    if stripattuNimi != u'admin' and checkPasswordVT4(salasana,joukkue['id'],joukkue['salasana']):
        session['joukkue'] = joukkue
        session['kirjautunut'] = 'regular'
        try:
            kNimi = db.getKilpailu(session['joukkue']['id'])['nimi']
            session['footerText'] = kNimi
        except Exception as e:
            debug(e)
            debug("Bugi: ei loydy kilpailua.")
            session['footerText'] = 'Ei loytynyt kilpailua!'
        session.pop('tempNimi',None)
        return redirect(url_for(u"joukkuelistaus"))

    # Tarkistetaan admin salasana.
    # Jos ok, niin mennaan mainPageen. 
    elif stripattuNimi == u"admin" and checkAdminPasswordVT4(salasana):
        session['kirjautunut'] = u'admin'
        session['footerText'] = 'ADMIN'
        session.pop('tempNimi',None)
        return redirect(url_for(u"mainPage"))
    else:
        pageVariables['errorSalasana'] = u"Salasana on väärä."
    return updatePage()

#########################################################################

@app.route(u'/joukkuelistaus', methods=[u'POST', u'GET'])
@auth
def joukkuelistaus():
    if 'joukkue' not in session:
        debug(u"VIRHE: joukkueId pitäisi olla määritelty tässä vaiheessa.")
    sarjat = db.getDataToJoukkuelistaus(session['footerText'])
    return render_template(u"joukkuelistaus.html",sarjat=sarjat)

#########################################################################

@app.route(u'/mainPage', methods=[u'GET'])
@authAdmin
def mainPage():
    kilpailut = db.getKilpailut()

    # Jos ei jostain syysta adminKilpailu ole sessiossa, niin tehdaan sen ny.
    # Ny se on ensimmainen tietokannasta haettu kilpailu.
    if 'adminKilpailu' not in session:
        if len(kilpailut) > 0:
            session['adminKilpailu'] = kilpailut[0]
        else:
            debug(u"Virhe: adminKilpailua ei ole luotu eikä sitä voi luoda!")
            return redirect(url_for(u"kirjaudu"))

    # Haetaan kaikki kilpailut ja muodostetaan niista query-ulril.
    for x in kilpailut:
        x['url'] = m.buildQuery(url_for(u"muokkaaKisa"),{'kNimi':x['nimi']})
    return render_template(u"mainPage.html",kilpailut=kilpailut)

#########################################################################

@app.route(u'/muokkaaKisa', methods=[u'POST',u'GET'])
@authAdmin
def muokkaaKisa():
    errorSarja = u""
    kilpailunNimi = u""
    sarjat = []

    if 'muokkaaSarjaSyote' not in session:
        session['muokkaaSarjaSyote'] = u""

    if 'muokkaaSarjaPoista' not in session:
        session['muokkaaSarjaPoista'] = None

    def updatePage():
        return render_template(u"muokkaaKisa.html",sarjat=sarjat,errorSarja=errorSarja)

    # Kerataan urlista tiedot.

    if request.method == u"GET":
        try:
            kilpailu = None
            args = request.args.get('kNimi')
            kilpailunNimi = m.unQuoteInput(args)
            kilpailu = db.getKilpailuByNimi(kilpailunNimi)
            if kilpailu is not None:
                session['adminKilpailu'] = kilpailu
                session['adminKilpailu']['rastitUrl'] = m.buildQuery(url_for(u"rastilistaus"),{'kNimi': kilpailu['nimi']})
                debug(session['adminKilpailu']['nimi'])
            else:
                debug(u"Virhe: kilpailua ei löydy")
                return redirect(url_for(u"mainPage"))
            sarjat = db.getSarjatByKisaNimi(session['adminKilpailu']['nimi'])

            # Muodostetaan linkit sarjojen muokkausta varten.
            for x in sarjat:
                x['url'] = m.buildQuery(url_for(u"muokkaaSarja"),{'sNimi':x['nimi'],'kNimi':session['adminKilpailu']['nimi']})
        except Exception as e:
            debug(e)

    # Painetaan Tallenna.
    if request.method == u"POST":

        sarjat = db.getSarjatByKisaNimi(session['adminKilpailu']['nimi'])
        snimi = u""
        poistaRuksi = None

        try:
            snimi = request.form.get(u"sarjanNimi").strip()
            poistaRuksi = request.form.get(u"poistaSarja")
            session['muokkaaSarjaSyote'] = snimi
            session['muokkaaSarjaPoista'] = poistaRuksi
        except Exception as e:
            debug(e)

        sarjat = db.getSarjatByKisaNimi(session['adminKilpailu']['nimi'])
        for x in sarjat:
            x['url'] = m.buildQuery(url_for(u"muokkaaSarja"),{'sNimi':x['nimi'],'kNimi':session['adminKilpailu']['nimi']})

        # Tarkistetaan syotteet.
        if len(snimi) == 0:
            errorSarja = u"Et voi antaa tyhjää nimeä."
            return updatePage()

        kohdeSarja = None

        for x in sarjat:
            if x['nimi'] == snimi:
                kohdeSarja = x
                break

        if kohdeSarja is not None and poistaRuksi is None:
            errorSarja = u"Et voi lisätä sarjaa. Kilpailussa on jo samanniminen sarja."
            return updatePage()

        if kohdeSarja is not None and poistaRuksi is not None:
            j = db.getJoukkueetBySarjaId(x['id'])
            if len(j) > 0:
                errorSarja = u"Et voi poistaa sarjaa. Sarjalla on joukkueita."
                return updatePage()

        if kohdeSarja is None and poistaRuksi is not None:
            errorSarja = u"Et voi poistaa sarjaa, sillä sitä ei ole olemassa."
            return updatePage()

        # Ei virheita! Joko tallennetaan tai poistetaan.

        # Poistetaan sarja.
        if kohdeSarja is not None and poistaRuksi is not None:
            db.poistaSarja(kohdeSarja)

        else:
            tallennettavaSarja = {}
            tallennettavaSarja['nimi'] = snimi
            tallennettavaSarja['kilpailu'] = session['adminKilpailu']['id']
            tallennettavaSarja['matka'] = u"-"
            tallennettavaSarja['kesto'] = 1
            tallennettavaSarja['alkuaika'] = None
            tallennettavaSarja['loppuaika'] = None
            db.lisaaSarja(tallennettavaSarja)
        session['muokkaaSarjaSyote'] = u""
        session['muokkaaSarjaPoista'] = None
        sarjat = db.getSarjatByKisaNimi(session['adminKilpailu']['nimi'])
        for x in sarjat:
            x['url'] = m.buildQuery(url_for(u"muokkaaSarja"),{'sNimi':x['nimi'],'kNimi':session['adminKilpailu']['nimi']})
        return updatePage()

    return updatePage()

#########################################################################

@app.route(u'/rastilistaus', methods=[u'POST',u'GET'])
@authAdmin
def rastilistaus():

    tempLon = u""
    tempLat = u""
    tempKoodi = u""
    tempPoista = None
    koodiLabelError = u""
    lanLabelError = u""
    lonLabelError = u""
    poistaError = u""
    kisaNimi = u""
    if 'rastiNow' not in session:
        session['rastiNow'] = None

    def updatePage():
        session['rastit'] = db.getRastit(session['adminKilpailu']['id'])
        for x in range(len(session['rastit'])):
            session['rastit'][x]['query'] = m.buildQuery(url_for(u"rastilistaus"),{'index':unicode(x),'kNimi':session['adminKilpailu']['nimi']})+u"#footer"

        return render_template(u"rastilistaus.html",
                               tempLon=tempLon,
                               tempLat=tempLat,
                               tempKoodi=tempKoodi,
                               lanLabelError=lanLabelError,
                               lonLabelError=lonLabelError,
                               koodiLabelError=koodiLabelError,
                               poistaError=poistaError)

    if request.method == u"GET":
        try:
            debug(request.args)
            kisaNimi = request.args.get('kNimi')
            session['rastit'] = db.getRastit(session['adminKilpailu']['id'])
            try:
                rastiIndex = request.args.get('index')
                debug(rastiIndex)
                session['rastiNow'] = session['rastit'][int(rastiIndex)]
            except Excpetion as e:
                debug(e)
            tempLon = session['rastiNow']['lon']
            tempLat = session['rastiNow']['lat']
            tempKoodi = session['rastiNow']['koodi']
            return updatePage()
        except Exception as e:
            debug(e)

    if request.method == u"POST":
        try:
            tempLon = request.form.get('lonLabel').strip()
            tempLat = request.form.get('lanLabel').strip()
            tempKoodi = request.form.get('koodiLabel').strip()
            tempPoista = request.form.get('poistaRasti')

            debug(request.form)

            # Tarkistukset.

            lat = None 
            lon = None 

            if tempPoista is not None:
                if session['rastiNow'] is not None:
                    if session['rastiNow']['lkm'] > 0:
                        poistaError = u"Rastia ei voi poistaa: rastilla on leimauksia."
                        return updatePage()
                    db.poistaRasti(session['rastiNow']['id'])
                    session['rastiNow'] = None
                    tempLon = u""
                    tempLat = u""
                    tempKoodi =  u""
                    tempPoista = u""
                    return updatePage()

            debug(u"yeah")

            try:
                lat = float(tempLat)
            except:
                lanLabelError = u"Anna liukuluku"

            try:
                lon = float(tempLon)
            except:
                lonLabelError = u"Anna liukuluku"

            if len(tempKoodi) == 0:
                koodiLabelError = u"Et voi antaa koodiksi pelkkää tyhjää."

            if len(lanLabelError) > 0 or len(lonLabelError) > 0 or len(koodiLabelError) > 0:
                return updatePage()

            # Tallennetaan rasti.

            # Muokataan olemassa olevaa rastia.
            if session['rastiNow'] is not None:
                db.paivitaRasti({'id': session['rastiNow']['id'],'lat': lat, 'lon': lon, 'koodi': tempKoodi, 'kilpailu': session['adminKilpailu']['id']})
            # Tallennetaan ihan uusi rasti.
            else:
                debug(u"yeah4")
                db.tallennaRasti({'lat': lat, 'lon': lon, 'koodi': tempKoodi,'kilpailu': session['adminKilpailu']['id']})

        except Exception as e:
            debug(e)
            return redirect(url_for(u"mainPage"))

    session['rastiNow'] = None
    tempLon = u""
    tempLat = u""
    tempKoodi =  u""
    tempPoista = u""

    return updatePage()

#########################################################################

@app.route(u'/muokkaaSarja', methods=[u'POST',u'GET'])
@authAdmin
def muokkaaSarja():

    joukkueet = []
    sarja = None
    kNimi = u""
    sNimi = u""
    jNimi = u""
    error = u""

    def refreshPage():
        return render_template(u"muokkaaSarja.html",
                               joukkueet=joukkueet,
                               sarja=sarja,
                               kNimi=kNimi,
                               sNimi=sNimi,
                               jNimi=jNimi,
                               error=error)

    if 'adminKilpailu' not in session:
        debug("Virhe: adminKilpailun taytyy olla maaritelty tassa vaiheessa.")
    if 'tempJoukkueNimi' not in session:
        session['tempJoukkueNimi'] = u""

    if request.method == u"GET":
        kilpailu = None
        try:
            kNimi = request.args.get('kNimi')
            sNimi = request.args.get('sNimi')

            kNimi = m.unQuoteInput(kNimi)
            sNimi = m.unQuoteInput(sNimi)

            # Periaatteessa pitaisi luottaa sessio-muuttuujaan, 
            # mutta otetaan nyt querysta kilpailun nimi.
            kilpailu = db.getKilpailuByNimi(kNimi)
            if kilpailu is None:
                debug(u"Kilpailua ei loytynyt. Palataan mainPageen.")
                return redirect(url_for(u"mainPage"))

            # Yritetaan hakea sarjaa kisan nimella.
            sarja = db.getSarjaByKisaNimi(kNimi,sNimi)
            if sarja is None:
                debug(u"Sarjaa ei loytynyt. Palataan mainPageen.")
                return redirect(url_for(u"mainPage"))

            joukkueet = db.getJoukkueetBySarjaId(sarja['id'])

            # Muodostetaan linkit joukkueita varten.
            for x in joukkueet:
                x['url'] = m.buildQuery(url_for(u"muokkaaJoukkue"),{'jNimi':x['nimi']})
        except Exception as e:
            debug(e)

    if request.method == u"POST":
        try:
            kNimi = request.form.get('kilpailuNimi')
            sNimi = request.form.get('sarjaNimi')
            jNimi = request.form.get('joukkueenNimi').strip()

            kilpailu = db.getKilpailuByNimi(kNimi)
            if kilpailu is None:
                debug(u"Kilpailua ei loytynyt. Palataan mainPageen.")
                return redirect(url_for(u"mainPage"))

            # Yritetaan hakea sarjaa kisan nimella.
            sarja = db.getSarjaByKisaNimi(kNimi,sNimi)
            if sarja is None:
                debug(u"Sarjaa ei loytynyt. Palataan mainPageen.")
                return redirect(url_for(u"mainPage"))

            j = db.getJoukkueByNimi(jNimi)

            joukkueet = db.getJoukkueetBySarjaId(sarja['id'])

            # Muodostetaan linkit joukkueita varten.
            for x in joukkueet:
                x['url'] = m.buildQuery(url_for(u"muokkaaJoukkue"),{'jNimi':x['nimi']})

            # Tarkistukset.

            if len(jNimi) == 0:
                error = u"Joukkueen nimi ei saa olla tyhjä."
                return refreshPage()

            if j is not None:
                error = u"Saman niminen joukkue on jo olemassa."
                return refeshPage()

            db.tallennaJoukkue({'nimi':jNimi,'sarja':sarja['id'],'jasenet':u'[]'})
            jNimi = u""
            joukkueet = db.getJoukkueetBySarjaId(sarja['id'])

        except Exception as e:
            debug(e)
    return refreshPage()

#########################################################################

@app.route(u'/muokkaaTupa', methods=[u'POST', u'GET'])
@authAdmin
def muokkaaTupa():
    debug(request.args)
    aika = u""
    koodi = u""
    jNimi = u""
    poista = None
    errorPoista = u""
    errorAika = u""
    alkuperainenJoukkue = u""
    tupaData = {'aika':u"", 'koodi':u"", 'nimi':u""}

    rastit = []
    try:
        rastit = db.getRastit(session['adminKilpailu']['id'])
    except Exception as e:
        debug(e)

    if 'muokkaaTupaAika' not in session:
        session['muokkaaTupaAika'] = u"ksdf"

    if 'muokkaaTupaPoista' not in session:
        session['muokkaaTupaPoista'] = None

    if 'alkuperainenTupa' not in session:
        session['alkuperainenTupa'] = None

    def updatePage():
        return render_template(u"muokkaaTupa.html",
                               rastit=rastit,
                               koodi=koodi,
                               errorAika=errorAika,
                               errorPoista=errorPoista,
                               aika=aika,
                               jNimi=jNimi,
                               alkuperainenJoukkue=alkuperainenJoukkue)
    def returnToPrevious():
        return redirect(m.buildQuery(url_for(u"muokkaaJoukkue"),{'jNimi':session['joukkue']['nimi']}))

    if request.method == u"GET":
        try:
            aika = m.unQuoteInput(request.args.get('aika'))
            koodi = m.unQuoteInput(request.args.get('koodi'))
            jNimi = m.unQuoteInput(request.args.get('jNimi'))
            alkuperainenJoukkue = jNimi
            tupaData = db.getTupaData(aika,koodi,jNimi)
            if tupaData is not None:
                session['alkuperainenTupa'] = {'rId': tupaData['rid'],
                                             'jId': tupaData['jid'],
                                             'aika': tupaData['aika']}
        except Exception as e:
            debug(e)
        return updatePage()

    if request.method == u"POST":
        try:
            debug(request.form)
            aika = request.form.get('aika')
            koodi = request.form.get('sKoodi')
            jNimi = request.form.get('jNimi')
            poista = request.form.get('poistaTupa')
            #uusi = request.form.get('uusiTupa')
            alkuperainenJoukkue = request.form.get('alkuperainenJoukkue')

            #if uusi is not None:
            #    session['alkuperainenTupa'] = None
            #    aika = u""
            #    koodi = u""
            #    updatePage()

            # Poisto...

            if poista is not None:
                if session['alkuperainenTupa'] is None:
                    return returnToPrevious()
                else:
                    db.poistaTupa(session['alkuperainenTupa'])
                    return returnToPrevious()

            # Tarkistukset.
            try:
                datetime.strptime(aika,u"%Y-%m-%d %H:%M:%S")
            except Exception as a:
                errorAika = u"Ajan täytyy olla muodoa yyyy-mm-dd hh:mm:ss"
                return updatePage()

            # Yritetaan tallentaa.


            # Tallenetaan ihan uusi...
            if len(errorAika) == 0 and session['alkuperainenTupa'] is None:
                r = db.getRastiByKilpailuAndKoodi(session['adminKilpailu']['id'],koodi)
                j = db.getJoukkueByNimi(alkuperainenJoukkue)
                db.tallennaTupa(r['id'],j['id'],aika)
                return returnToPrevious()

            # Tallennetaan olemassa oleva rasti.
            elif len(errorAika) == 0 and session['alkuperainenTupa'] is not None:
                r = db.getRastiByKilpailuAndKoodi(session['adminKilpailu']['id'],koodi)
                j = db.getJoukkueByNimi(alkuperainenJoukkue)
                debug(u"muokataan")
                db.muokkaaTupa(session['alkuperainenTupa'],r['id'],j['id'],aika)
                debug(u"muokataan2")
                return returnToPrevious()

        except Exception as e:
            debug(e)
            return returnToPrevious()

        return updatePage()

    return updatePage()

#########################################################################

@app.route(u'/muokkaaJoukkue', methods=[u'POST', u'GET'])
@auth
def muokkaaJoukkue():

    # Sivukohtaisen muuttujat
    kNimi = u""
    joukkueNimi = u""
    sarjat = []
    joukkueNimiError = u""
    jasenError = u""
    poistoError = u""
    rastit = []
    kisaRastit = []
    salasana = u""
    salasanaError = u""

    if session['kirjautunut'] == u"admin":
        try:
            args = request.args.get('jNimi')
            jNimi = m.unQuoteInput(args)
            joukkue = db.getJoukkueByNimi(jNimi)
            if joukkue is None:
                debug("Virhe: joukkuetta ei löyty. Palataan mainPageen.")
                return redirect(url_for(u"mainPage"))
            else:
                session['joukkue'] = joukkue

        except Exception as e:
            debug(e)

    if 'joukkue' not in session:
        debug(u"VIRHE: joukkue pitaisi olla maaritelty jo.")
    if 'kirjautunut' not in session:
        debug(u"VIRHE: kirjautunut pitaisi olla maaritelty jo.")

    # Tahan admin tarkistukset.

    if 'tempJasenet' not in session:
        session['tempJasenet'] = [u"",u"",u"",u"",u""]
    if 'tempSarjaNimi' not in session:
        session['tempSarja'] = u""
    if 'tempJNimi' not in session:
        session['tempJNimi'] = u""
    if 'nykyinenSarja' not in session:
        session['nykyinenSarja'] = u""

    # TODO: admin ei voi ottaa sarjoja footerTextista!
    kisa = db.getKilpailu(session['joukkue']['id'])
    sarjat = db.getSarjatByKisaNimi(kisa['nimi'])

    # Haetaan joukkueen rastileimaukset.
    rastit = db.haeJoukkueenRastileimaukset(session['joukkue']['id'])
    kisaRastit = db.getRastit(session['adminKilpailu']['id'])
    debug(kisaRastit)

    for x in rastit:
        x['href'] = m.buildQuery(url_for(u"muokkaaTupa"),
                {'aika':x['tAika'],'koodi':x['rKoodi'],'jNimi':session['joukkue']['nimi']})
    # Sivun uudelleen piirto funktio.
    def updatePage():
        return render_template(u"muokkaaJoukkue.html",
                               sarjat=sarjat,
                               joukkueNimiError=joukkueNimiError,
                               jasenError=jasenError,
                               poistoError=poistoError,
                               salasanaError=salasanaError,
                               kisaRastit=kisaRastit,
                               rastit=rastit)

    if request.method == u"GET":
        session['tempJNimi'] = session['joukkue']['nimi']
        session['nykyinenSarja'] = db.getSarjaByJoukkueId(session['joukkue']['id'])['nimi']
        session['tempJasenet'] = createJasentenNimet(5,session['joukkue']['jasenet'])

    if request.method == u"POST":

        # Lisataan rasti.

        if request.form.get('lisaaRasti') is not None:
            newRastiUrl = m.buildQuery(url_for(u"muokkaaTupa"),{'aika':u"",'koodi':u"",'jNimi':session['joukkue']['nimi']})
            return redirect(newRastiUrl)

        # Admin tilaa varten.
        poista = None

        # Otetaan talteen lomakkeen tiedot.
        try:
            session['tempJNimi'] = request.form.get(u'joukkueNimi').strip()
            session['nykyinenSarja'] = request.form.get(u'SARJA')
            poista = request.form.get(u'poistaJoukkue')
            if session['kirjautunut'] == u"regular":
                salasana = request.form.get(u"newSalasana")
            jasenet = []
            for x in range(5):
                jasenet.append(request.form.get(u"Jäsen"+ unicode(x+1)).strip())
            session['tempJasenet'] = createJasentenNimet(5,jasenet)
        except Exception as e:
            debug(e)

        # Tarkistetaan lomaketiedot.

        # Tahan joukkueen poisto.
        if session['kirjautunut'] == u"admin" and poista is not None:
            if len(rastit) > 0:
                poistoError = u"Poistoa ei suoriteta: joukkueella leimauksia."
                return updatePage()
            else:
                db.poistaJoukkue(session['joukkue']['nimi'])
                session.pop('tempJNimi',None)
                session.pop('tempSarja',None)
                session.pop('nykyinenSarja',None)
                session.pop('tempJasenet',None)
                return redirect(url_for(u"mainPage"))

        # Onko joukkueen nimi tyhja?
        if len(session['tempJNimi']) == 0:
            joukkueNimiError = u"joukkue nimi ei saa olla tyhjä"
            return updatePage()

        # Onko tuon niminen joukkue jo olemassa?
        j = db.getJoukkueByNimi(session['tempJNimi'])
        if j is not None and j['nimi'] == session['tempJNimi'] and session['joukkue']['id'] != j['id']:
            joukkueNimiError = u"Saman niminen joukkue on jo olemassa."
            return updatePage()

        # Onko jasenia tarpeeksi?
        if len([x for x in session['tempJasenet'] if len(x) > 0]) < 2:
            jasenError = u"Jasenia taytyy olla vahintaan 2."
            return updatePage()

        # Jos salasanakenttaan on annettu jotain, niin luodaan uusi salasana.
        if len(salasana) > 0:
            d = hashlib.sha512()
            d.update(str(session['joukkue']['id']))
            d.update(salasana)
            # Ei ehka pitaisi taalla tehda naita salasanajuttuja. Ehka
            # tietokannassa....
            session['joukkue']['salasana'] = d.hexdigest().decode("UTF-8")

        # Jos tanne asti paastiin, niin tallennetaan. TODO: tarkista viela
        # poista juttu admin tilassa.

        kisa = db.getKilpailu(session['joukkue']['id'])
        newSarja = db.getSarjaByKisaNimi(kisa['nimi'],session['nykyinenSarja'])

        # Jos ei loydy sarjaa, niin huono homma. Palataan
        # jonnekin toiselle sivulle.
        if newSarja is None:
            debug("newSarja == None. Ei hyva.")
            if session['kirjautunut'] == u"admin":
                return redirect(url_for(u'mainPage'))
            elif session['kirjautunut'] == u"regular":
                return redirect(url_for(u'joukkuelistaus'))
        js = [x for x in session['tempJasenet'] if len(x) > 0]
        newJoukkue = {'id': session['joukkue']['id'],'nimi':session['tempJNimi'], 'sarja':newSarja['id'],'jasenet':unicode(json.dumps(js)), 'salasana': session['joukkue']['salasana']}

        if db.paivitaJoukkue(newJoukkue):
            # Hommaudutaan naista eroon. En tieda onko pakko...
            session['joukkue'] = db.getJoukkueById(session['joukkue']['id'])
            session.pop('tempJNimi',None)
            session.pop('nykyinenSarja',None)
            session.pop('tempJasenet',None)
        if session['kirjautunut'] == u'regular':
            return redirect(url_for(u"joukkuelistaus"))
        elif session['kirjautunut'] == u'admin':
            return redirect(m.buildQuery(url_for(u"muokkaaSarja"),{'sNimi':newSarja['nimi'],'kNimi':kisa['nimi']}))

    return updatePage()

#########################################################################

@app.route(u'/logoutPage', methods=[u'POST', u'GET'])
@auth
def logoutPage():
    if 'kirjautunut' not in session:
        debug(u"VIRHE: kirjautunut pitaisi olla maaritelty.")
    if 'joukkue' not in session:
        debug(u"VIRHE: joukkue pitaisi olla maaritelty.")

    poistutaan = False

    # Selvitetaan se, etta onko logout nappia painettu.
    try:
        if request.form.get('logoutButton') is not None:
            poistutaan = True
        else:
            poistutaan = False
    except Exception as e:
        debug(e)

    # Poistutaan siis.
    if poistutaan:
        session.clear()
        return redirect(url_for(u"kirjaudu"))

    # Jos tavallinen kayttaja, niin...
    if session['kirjautunut'] == u"regular":
        return render_template("logoutPage.html")
    # Jos admin , niin...
    if session['kirjautunut'] == u"admin":
        return render_template("logoutPage.html")
    debug(u"Huonosti kävi!")
    debug(u"session[kirjautunut] == {0}".format(session['kirjautunut']))
    debug(u"joukkue == {0}".format(session['joukkue']))

#########################################################################

# Vt4 versio. Tassa olisi ehka hyva hetki hakea digest tietokannasta 
# eika kuljetella sita mukana session-muuttujassa kaikkialla...
def checkPasswordVT4(salasana, i,usrDigest):
    # Luodaan digest kayttajan antamasta salasanasta.
    token = hashlib.sha512()
    token.update(str(i))
    token.update(salasana)
    digest = token.hexdigest()
    return digest == usrDigest

#########################################################################

def checkAdminPasswordVT4(pwd):
    token = hashlib.sha512()
    token.update("erkkiajaamopolla")
    token.update(pwd)
    digest = "EY\x9d\xc5\x9f\xa1\x91\xbd\x90\xcfEu\xe8\x84,\xa5\x9a\xf6:\xa2\x11>\xee\xe2\xf6\x9c\xa1\xf2>\xeaK\x9dQF\x82\xcc\xbap\xf8A\x13\xe3\xb2lF\xcc\x9cG\xd3\xce\xabq,e\xe6\xff\xb0\x80\x14\x9e\xc7U>\xa0"
    return token.digest() == digest

###############################################################################

# Luo listan jasenista. @maxJasenia on jaseneten lukumaara.
# Tama funktio olettaa, etta sessioMuuttuja 'joukkue' on alustettu
# joukkueoliolla.
def createJasentenNimet(maxJasenia,jasenet):
    j = []
    if not isinstance(jasenet,list):
        return [u''] * maxJasenia
    jasenet = [x for x in jasenet if len(x) > 0]
    jasenet.sort()
    for x in range(maxJasenia):
        try:
            j.append(jasenet[x])
        except:
            j.append(u"")
    return j

###############################################################################

if __name__ == '__main__':
    app.debug = True
    app.run(debug=True)
