#!/usr/bin/python
# -*- coding: utf-8 -*-

from flask import Flask, g, session, redirect, url_for, escape, request, Response, render_template, make_response
import xml.etree.ElementTree as ET
#import os
#import sys
import json
from functools import wraps
from copy import deepcopy
import hashlib
from datetime import datetime
import vt4database as db
import myWeb as m

app = Flask(__name__)
app.secret_key = u'\xf9%\xf8\xd2V+[\x1b\xfd\xac\xa6\xe9\x7f\xffmEO}\x1fgd\x1c\xfbm'
app.jinja_env.trim_blocks = True
app.jinja_env.lstrip_blocks = True
m.debug(u"aloitetaan")

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

@app.route(u'/', methods=['GET','POST'])
def root():
    m.debug(u"ahhaaaa")

    # Luodaan sessiomuuttujat. Tassa on hyva paikka muuttujien 
    # alustamiselle, silla kaikkien taytyy joka tapauksesa kirjautua ensin.
    if 'kirjautunut' not in session:
        session['kirjautunut'] = None

    if 'kilpailu' not in session:
        session['kilpailu'] = None

    pass

#########################################################################

@app.route(u'/kirjaudu', methods=['GET','POST'])
def kirjaudu():
    m.debug(request.form)


    kilpailut = []
    if 'updateFooter' not in session:
        session['updateFooter'] = False

    # Luodaan sessiomuuttujat. Tassa on hyva paikka muuttujien 
    # alustamiselle, silla kaikkien taytyy joka tapauksesa kirjautua ensin.

    if 'kirjautunut' not in session:
        session['kirjautunut'] = None

    if 'kilpailu' not in session:
        session['kilpailu'] = None

    try:
        kilpailut = map(lambda x: x['nimi'], db.getKilpailut())
    except:
        pass

    data = {'errorTunnus': u"",
            'errorSalasana': u"",
            'nimi': u"",
            'salasana': u"",
            'kilpailu': u"",
            'nextState': u"",
            'laheta': None}

    def mkResponse():
        m.debug(u"mkResponse")
        m.debug(data)
        m.debug(u"joo")
        resp = None

        if data['nextState'] == u"kirjaudu":
            resp = make_response(render_template("kirjaudu.xml",
                                                 errorTunnus=data['errorTunnus'],
                                                 errorSalasana=data['errorSalasana'],
                                                 nimi=data['nimi'],
                                                 kilpailut=kilpailut))
        elif data['nextState'] == u"joukkuelistaus":
            session['updateFooter'] = True
            return redirect(url_for(u"joukkuelistaus"))
        elif data['nextState'] == u"mainPage":
            session['updateFooter'] = True
            return redirect(url_for(u"mainPage"))
        resp.charset= "UTF-8"
        resp.headers.extend({'nextState': data['nextState']})
        if session['updateFooter'] == u"clear":
            resp.headers.extend({'updateFooter': session['updateFooter']})
        else:
            resp.headers.extend({'updateFooter': False})
        resp.mimetype = "text/xml"
        return resp

    # POST....

    if request.method == 'POST':
        try:
            data['nimi'] = request.form.get('tunnus', u"").strip()
            data['salasana'] = request.form.get('salasana', u"").strip()
            data['kilpailu'] = request.form.get('alasveto', u"").strip()
            session['adminKilpailu'] = db.getKilpailuByNimi(data['kilpailu'])
            data = checkKirjauduForm(data)
            return mkResponse()
        except Exception as e:
            m.debug(e)

    # GET....
    elif request.method == 'GET':
        try:
            request.form.get(u"newSession")
            session.clear()
            session['updateFooter'] = u"clear"
        except Exception as e:
            m.debug(u"ählämmmmmm")
            m.debug(e)
        data['nextState'] = u"kirjaudu"

    return mkResponse()

#########################################################################

@app.route(u'/muokkaaKisa', methods=[u'GET',u'POST'])
def muokkaaKisa():
    errorSarja = u""
    kilpailunNimi = u""
    sarjat = []

    if 'muokkaaSarjaSyote' not in session:
        session['muokkaaSarjaSyote'] = u""

    if 'muokkaaSarjaPoista' not in session:
        session['muokkaaSarjaPoista'] = None

    def updatePage():
        resp = make_response(render_template(u"muokkaaKisa.xml",sarjat=sarjat,errorSarja=errorSarja))
        resp.charset= "UTF-8"
        resp.headers.extend({'nextState': u"muokkaaKisa"})
        resp.headers.extend({'updateFooter': session['updateFooter']})
        resp.mimetype = "text/xml"
        return resp
#        return render_template(u"muokkaaKisa.xml",sarjat=sarjat,errorSarja=errorSarja)

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
                m.debug(session['adminKilpailu']['nimi'])
            else:
                m.debug(u"Virhe: kilpailua ei löydy")
                return redirect(url_for(u"mainPage"))
            sarjat = db.getSarjatByKisaNimi(session['adminKilpailu']['nimi'])

            # Muodostetaan linkit sarjojen muokkausta varten.
            for x in sarjat:
                x['url'] = m.buildQuery(url_for(u"muokkaaSarja"),{'sNimi':x['nimi'],'kNimi':session['adminKilpailu']['nimi']})
        except Exception as e:
            m.debug(e)

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
            m.debug(e)

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
@app.route(u'/logoutPage', methods=[u'GET'])
def logoutPage():
    if 'kirjautunut' not in session:
        m.debug(u"VIRHE: kirjautunut pitaisi olla maaritelty.")
    if 'joukkue' not in session:
        m.debug(u"VIRHE: joukkue pitaisi olla maaritelty.")

#    poistutaan = False

    resp = make_response(render_template("logout.xml"))
    resp.charset= "UTF-8"
    resp.headers.extend({'nextState': u"logout"})
    resp.headers.extend({'updateFooter': session['updateFooter']})
    resp.mimetype = "text/xml"
    return resp

    # Selvitetaan se, etta onko logout nappia painettu.
#    try:
#        if request.form.get('logoutButton') is not None:
#            poistutaan = True
#        else:
#            poistutaan = False
#    except Exception as e:
#        debug(e)

    # Poistutaan siis.
#    if poistutaan:
#        session.clear()
#        return redirect(url_for(u"kirjaudu"))
#
    # Jos tavallinen kayttaja, niin...
#    if session['kirjautunut'] == u"regular":
#        return render_template("logoutPage.html")
#    # Jos admin , niin...
#    if session['kirjautunut'] == u"admin":
#        return render_template("logoutPage.html")
#    m.debug(u"Huonosti kävi!")
#    m.debug(u"session[kirjautunut] == {0}".format(session['kirjautunut']))
#    m.debug(u"joukkue == {0}".format(session['joukkue']))

#########################################################################

def checkKirjauduForm(kirjauduData):
    data = deepcopy(kirjauduData)
    m.debug(data)

    # Tarkistetaan nimiasiat.

    if len(data['nimi']) == 0:
        data['errorTunnus'] = errorTunnus = u"Nimi ei saa olla tyhjä."
        data['nextState'] = u"kirjaudu"
        return data

    elif data['nimi'] == u"admin":
        pass

    elif db.getJoukkueByNimi(data['nimi']) == None:
        data['errorTunnus'] = u"Joukkuetta ei ole olemassa."
        data['nextState'] = u"kirjaudu"
        return data

    # Tarkistetaan salasanaasiat.

    if len(data['salasana']) == 0:
        data['nextState'] = u"kirjaudu"
        data['errorSalasana'] = u"Salasana ei voi olla tyhjä."
        return data

    elif data['nimi'] == u"admin" and db.checkAdminPasswordVT4(data['salasana']):
        session['footerText'] = u"ADMIN"
        data['nextState'] = u"mainPage"
        session['kirjautunut'] = u"admin"
        return data

    elif db.checkPasswordVT5(data['salasana'],data['nimi']):
        data['nextState'] = u"joukkuelistaus"
        session['kirjautunut'] = u"regular"
        session['joukkue'] = db.getJoukkueByNimi(data['nimi'])
        try:
            session['footerText'] = db.getKilpailu(session['joukkue']['id'])['nimi']
            m.debug(u"footerText")
            m.debug(session['footerText'])
        except Exception as e:
            m.debug(e)
        return data

    else:
        data['errorSalasana'] = u"Salasana on väärä."
        data['nextState'] = u"kirjaudu"
        return data

    m.debug(u"Tänne ei pitäisi päätyä koskaan")

#########################################################################

@app.route(u'/muokkaaJoukkue', methods=[u'POST', u'GET'])
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
                m.debug("Virhe: joukkuetta ei löyty. Palataan mainPageen.")
                return redirect(url_for(u"mainPage"))
            else:
                session['joukkue'] = joukkue

        except Exception as e:
            m.debug(e)

    if 'joukkue' not in session:
        m.debug(u"VIRHE: joukkue pitaisi olla maaritelty jo.")
    if 'kirjautunut' not in session:
        m.debug(u"VIRHE: kirjautunut pitaisi olla maaritelty jo.")

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

    for x in rastit:
        x['href'] = m.buildQuery(url_for(u"muokkaaTupa"),
                {'aika':x['tAika'],'koodi':x['rKoodi'],'jNimi':session['joukkue']['nimi']})
    # Sivun uudelleen piirto funktio.
    def updatePage():
        resp = make_response(render_template("muokkaaJoukkue.xml",
                                             sarjat=sarjat,
                                             joukkueNimiError=joukkueNimiError,
                                             jasenError=jasenError,
                                             poistoError=poistoError,
                                             salasanaError=salasanaError,
                                             kisaRastit=kisaRastit,
                                             rastit=rastit))
#        m.debug(render_template("muokkaaJoukkue.xml",
#                                             sarjat=sarjat,
#                                             joukkueNimiError=joukkueNimiError,
#                                             jasenError=jasenError,
#                                             poistoError=poistoError,
#                                             salasanaError=salasanaError,
#                                             kisaRastit=kisaRastit,
#                                             rastit=rastit))
        resp.charset= "UTF-8"
        resp.headers.extend({'nextState': u"muokkaaJoukkue"})
        resp.headers.extend({'updateFooter': session['updateFooter']})
        resp.mimetype = "text/xml"
        return resp

    if request.method == u"GET":
        session['tempJNimi'] = session['joukkue']['nimi']
        session['nykyinenSarja'] = db.getSarjaByJoukkueId(session['joukkue']['id'])['nimi']
        session['tempJasenet'] = createJasentenNimet(5,session['joukkue']['jasenet'])

    if request.method == u"POST":

        # Lisataan rasti.

        if request.form.get('lisaaRasti') is not None:
            # TODO.....
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
            m.debug(e)

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
            m.debug("newSarja == None. Ei hyva.")
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

@app.route(u'/joukkuelistaus', methods=[u'POST', u'GET'])
@auth
def joukkuelistaus():
    sarjat = db.getDataToJoukkuelistaus(session['footerText'])
    resp = make_response(render_template("joukkuelistaus.xml",
                                             sarjat=sarjat))
    resp.charset= "UTF-8"
    resp.headers.extend({'nextState': u"joukkuelistaus"})
    resp.headers.extend({'updateFooter': session['updateFooter']})
    resp.mimetype = "text/xml"
    return resp

#########################################################################

@app.route(u'/mainPage', methods=[u'GET'])
def mainPage():
    kilpailut = db.getKilpailut()

    # Jos ei jostain syysta adminKilpailu ole sessiossa, niin tehdaan sen ny.
    # Ny se on ensimmainen tietokannasta haettu kilpailu.
    if 'adminKilpailu' not in session:
        if len(kilpailut) > 0:
            session['adminKilpailu'] = kilpailut[0]
        else:
            m.debug(u"Virhe: adminKilpailua ei ole luotu eikä sitä voi luoda!")
            return redirect(url_for(u"kirjaudu"))

    resp = make_response(render_template("mainPage.xml", kilpailut=kilpailut))
    resp.charset= "UTF-8"
    resp.headers.extend({'nextState': u"mainPage"})
    resp.headers.extend({'updateFooter': session['updateFooter']})
    resp.mimetype = "text/xml"
    return resp

#########################################################################

# Taalla luodaan footer asiakasta varten. Kokeillaan tehda ilman 
# templateja tama.
@app.route(u'/footerResponse', methods=['GET'])
def footerResponse():
    error = False
    if 'kirjautunut' not in session:
        error = True
        m.debug(u"footerResponce: ei-kirjautunut")
    if 'footerText' not in session:
        error = True
        m.debug(u"footerResponce: ei footer tekstia.")

    # Ilmeisesti ei oltu kirjauduttu. Siita siis virhe asiakkaalle.
    if error:
        r = make_response(u"ei-kirjautumista",403)
        r.charset= "UTF-8"
        r.mimetype = "text"
        return r

    # Ilmeisesti ollaan sitten kirauduttu...
    xml = """<?xml version="1.0" encoding="UTF-8"?><div id="footer"/>"""
    root = ET.fromstring(xml)
    root.attrib['xmlns'] = "http://www.w3.org/1999/xhtml"
    footer  = ET.SubElement(root,"footer")
    pFooterText  = ET.SubElement(footer,"p")
    pFooterText.text = session['footerText']
    pKilpailuNimi = ET.SubElement(footer,"p")
    pKilpailuNimi.text = session['adminKilpailu']['nimi']
    pKilpailuNimi.attrib['id'] = "footerKilpailuNimi"
    pKilpailuNimi.attrib['class'] = "hidden"
    pMuokkaaJoukkue  = None
    pJoukkueListaus  = None
    pMainpage  = None
    if session['kirjautunut'] == u"regular":
        pMuokkaaJoukkue  = ET.SubElement(footer,"p")
        aMuokkaaJoukkue  = ET.SubElement(pMuokkaaJoukkue,"a")
        aMuokkaaJoukkue.text = session['joukkue']['nimi']
        aMuokkaaJoukkue.attrib['href'] = u"";
        aMuokkaaJoukkue.attrib['id'] = u"aMuokkaaJoukkue"
        pJoukkueListaus  = ET.SubElement(footer,"p")
        aJoukkueListaus  = ET.SubElement(pJoukkueListaus,"a")
        aJoukkueListaus.text = u"Joukkuelistaus"
        aJoukkueListaus.attrib['href'] = u"";
        aJoukkueListaus.attrib['id'] = u"aJoukkueListaus"
    elif session['kirjautunut'] == u"admin":
        pMainpage  = ET.SubElement(footer,"p")
        aMainpage  = ET.SubElement(pMainpage,"a")
        aMainpage.text = u"Pääsivu"
        aMainpage.attrib['id'] = u"aMainPage"
        aMainpage.attrib['href'] = u""
        pRastilistaus  = ET.SubElement(footer,"p")
        aRastilistaus  = ET.SubElement(pRastilistaus,"a")
        aRastilistaus.text = u"Rastilistaus"
        aRastilistaus.attrib['id'] = u"aRastilistaus"
        aRastilistaus.attrib['href'] = u""
    else:
        m.debug(u"VIRHE: tanne ei pitaisi paatya....")

    pLogout = ET.SubElement(footer,"p")
    aLogout = ET.SubElement(pLogout,"a")
    aLogout.text = u"Kirjaudu ulos"
    aLogout.attrib['id'] = u"aKirjauduUlos"
    aLogout.attrib['href'] = u""

    #resp = make_response(render_template("kokeilu.xml",p=p))
    resp = make_response(ET.tostring(root, encoding="UTF-8", method="xml"))
    m.debug(u"ooooollraiiiiiiT")
    m.debug(ET.tostring(root, encoding="UTF-8", method="xml"))
    m.debug(u"ooooollraiiiiiiT2")
    resp.charset= "UTF-8"
    resp.mimetype = "text/xml"
    return resp

#########################################################################

@app.route(u'/rastilistaus', methods=[u'POST',u'GET'])
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

        resp = make_response(render_template(u"rastilistaus.xml",
                             tempLon=tempLon,
                             tempLat=tempLat,
                             tempKoodi=tempKoodi,
                             lanLabelError=lanLabelError,
                             lonLabelError=lonLabelError,
                             koodiLabelError=koodiLabelError,
                             poistaError=poistaError))
        resp.charset= "UTF-8"
        resp.headers.extend({'nextState': u"rastilistaus"})
        resp.headers.extend({'updateFooter': session['updateFooter']})
        resp.mimetype = "text/xml"
        return resp

    if request.method == u"GET":
        try:
            kisaNimi = request.args.get('kNimi')
            session['rastit'] = db.getRastit(session['adminKilpailu']['id'])
            try:
                rastiIndex = request.args.get('index')
                session['rastiNow'] = session['rastit'][int(rastiIndex)]
            except Exception as e:
                m.debug(e)
            tempLon = session['rastiNow']['lon']
            tempLat = session['rastiNow']['lat']
            tempKoodi = session['rastiNow']['koodi']
            return updatePage()
        except Exception as e:
            m.debug(e)

    if request.method == u"POST":
        try:
            tempLon = request.form.get('lonLabel').strip()
            tempLat = request.form.get('lanLabel').strip()
            tempKoodi = request.form.get('koodiLabel').strip()
            tempPoista = request.form.get('poistaRasti')

            # Tarkistukset.

            lat = None 
            lon = None 

            if tempPoista is not None:
                if session['rastiNow'] is not None:
                    m.debug(session['rastiNow'])
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
                db.tallennaRasti({'lat': lat, 'lon': lon, 'koodi': tempKoodi,'kilpailu': session['adminKilpailu']['id']})

        except Exception as e:
            m.debug(e)
            return redirect(url_for(u"mainPage"))

    session['rastiNow'] = None
    tempLon = u""
    tempLat = u""
    tempKoodi =  u""
    tempPoista = u""

    return updatePage()

#########################################################################

@app.route(u'/muokkaaSarja', methods=[u'POST',u'GET'])
def muokkaaSarja():

    joukkueet = []
    sarja = None
    kNimi = u""
    sNimi = u""
    jNimi = u""
    error = u""

    def refreshPage():
        resp = make_response(render_template(u"muokkaaSarja.xml",
                               joukkueet=joukkueet,
                               sarja=sarja,
                               kNimi=kNimi,
                               sNimi=sNimi,
                               jNimi=jNimi,
                               error=error))
        resp.charset= "UTF-8"
        resp.headers.extend({'nextState': u"muokkaaSarja"})
        resp.headers.extend({'updateFooter': session['updateFooter']})
        resp.mimetype = "text/xml"
        return resp

    if 'adminKilpailu' not in session:
        m.debug("Virhe: adminKilpailun taytyy olla maaritelty tassa vaiheessa.")
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
                m.debug(u"Kilpailua ei loytynyt. Palataan mainPageen.")
                return redirect(url_for(u"mainPage"))

            # Yritetaan hakea sarjaa kisan nimella.
            sarja = db.getSarjaByKisaNimi(kNimi,sNimi)
            if sarja is None:
                m.debug(u"Sarjaa ei loytynyt. Palataan mainPageen.")
                return redirect(url_for(u"mainPage"))

            joukkueet = db.getJoukkueetBySarjaId(sarja['id'])

            # Muodostetaan linkit joukkueita varten.
            for x in joukkueet:
                x['url'] = m.buildQuery(url_for(u"muokkaaJoukkue"),{'jNimi':x['nimi']})
        except Exception as e:
            m.debug(e)

    if request.method == u"POST":
        try:
            kNimi = request.form.get('kilpailuNimi')
            sNimi = request.form.get('sarjaNimi')
            jNimi = request.form.get('joukkueenNimi').strip()

            kilpailu = db.getKilpailuByNimi(kNimi)
            if kilpailu is None:
                m.debug(u"Kilpailua ei loytynyt. Palataan mainPageen.")
                return redirect(url_for(u"mainPage"))

            # Yritetaan hakea sarjaa kisan nimella.
            sarja = db.getSarjaByKisaNimi(kNimi,sNimi)
            if sarja is None:
                m.debug(u"Sarjaa ei loytynyt. Palataan mainPageen.")
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
            m.debug(e)
    return refreshPage()

#########################################################################

@app.route(u'/muokkaaTupa', methods=[u'POST', u'GET'])
def muokkaaTupa():
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
        m.debug(e)

    if 'muokkaaTupaAika' not in session:
        session['muokkaaTupaAika'] = u"ksdf"

    if 'muokkaaTupaPoista' not in session:
        session['muokkaaTupaPoista'] = None

    if 'alkuperainenTupa' not in session:
        session['alkuperainenTupa'] = None

    def updatePage():
        # TODO:: tee loppuun....
        resp = make_response(render_template(u"muokkaaTupa.xml",
                               rastit=rastit,
                               koodi=koodi,
                               errorAika=errorAika,
                               errorPoista=errorPoista,
                               aika=aika,
                               jNimi=jNimi,
                               alkuperainenJoukkue=alkuperainenJoukkue))
        resp.charset= "UTF-8"
        resp.headers.extend({'nextState': u"muokkaaTupa"})
        resp.headers.extend({'updateFooter': session['updateFooter']})
        resp.mimetype = "text/xml"
        return resp
    def returnToPrevious():
#        return redirect(url_for(u"muokkaaJoukkue"))
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
            m.debug(e)
        return updatePage()

    if request.method == u"POST":
        m.debug(request.form)
        try:
            aika = request.form.get('aika')
            m.debug(u"aika:")
            m.debug(aika)
            koodi = request.form.get('sKoodi')
            jNimi = request.form.get('jNimi')
            poista = request.form.get('poistaTupa')
            alkuperainenJoukkue = request.form.get('alkuperainenJoukkue')

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
                db.muokkaaTupa(session['alkuperainenTupa'],r['id'],j['id'],aika)
                return returnToPrevious()

        except Exception as e:
            m.debug(e)
            return returnToPrevious()

        return updatePage()

    return updatePage()

#########################################################################

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
