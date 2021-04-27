# -*- coding: utf-8 -*-
from optparse import OptionParser
import inspect
import re
from functools import wraps
import sys, traceback
from flask import Flask, render_template, request, make_response, redirect, url_for, session
from google.appengine.ext import ndb
from wtforms_appengine.ndb import model_form
from wtforms_appengine.fields import KeyPropertyField
from google.appengine.api import users
from flask_wtf import FlaskForm
from wtforms import SelectField, HiddenField, StringField, ValidationError
from wtforms.validators import InputRequired
from wtforms import validators
from datetime import datetime
from luokat import *
from database import *
from initialData import *

app = Flask(__name__)
app.secret_key = u'huhhahhei'

#########################################################################

# Decoraattori, joka ottaa viime kadessa virheen kiinni jotta sovellus ei kaadu
# lopullisesti. Virhe tulostetaan nyt konsoliin, ja asiakkaalle lahetetaan
# virhe sivu.
def bugTracker(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            # Tahan pitaisi laittaa esim. logitus tiedostoon tms.
            # Toisaalta tama menee google cloud enginessa jonnekin fiksuun
            # paikkaan... tai sitten ei.
            exc_type, exc_value, exc_traceback = sys.exc_info()
            traceback.print_tb(exc_traceback,limit=10,file=sys.stdout)
            print unicode(e)
            virhe = u"Valitettavasti tapahtui jokin virhe. Ohjelma on todennakoisesti kohdannut bugin josta ei toivuttu. Harmin paikka."
            return make_response(render_template(u"virhe.html",virhe=virhe),500)
    return decorated

#########################################################################

def auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        user = users.get_current_user()
        if user:
            return f(*args, **kwargs)
        else:
            return redirect(url_for(u'login'))
#        try:
#            if session['user'] != u"ahaa":
#                raise Exception
#        except:
#            return redirect(url_for(u'login'))
#        return f(*args, **kwargs)
    return decorated

#########################################################################

#########################
### Routet            ###
#########################

####################################################################################################

# Logout sivu
@app.route('/logout')
@bugTracker
def root():
    return "Heippa world!"

####################################################################################################

# Kirjaudutaan sisään käyttäen googlen autentikointia
@app.route('/login')
@bugTracker
def login():
        user = users.get_current_user()
        if user:
            nickname = user.nickname()
            logout_url = users.create_logout_url('/logout')
            greeting = 'Welcome, {}! (<a href="{}">sign out</a>)'.format(
                nickname, logout_url)
        else:
            login_url = users.create_login_url('/kilpailut')
            greeting = '<a href="{}">Sign in</a>'.format(login_url)
        return '<html><body>{}</body></html>'.format(greeting)

####################################################################################################

@app.route('/info')
@bugTracker
@auth
def info(message):
    return render_template('info.html',message=message)

####################################################################################################

# Tulostaa kaikki kilpailut.
@app.route('/kilpailut', methods=['GET'])
@bugTracker
@auth
def allKilpailut():
    kilpailut = Kilpailu.query().fetch()
    return render_template('allKilpailut.html',kilpailut=kilpailut)

####################################################################################################

# Tulostaa yksittaisen kilpailun. Tassa voi luoda/muokata/tuhota kilpailun.
@app.route('/kilpailut/<kilpailu_id>', methods=['GET','POST'])
@bugTracker
@auth
def kilpailut(kilpailu_id):

    kilpailu = Kilpailu()

    if kilpailu_id != "0":
        try:
            kilpailu = getKilpailu(kilpailu_id) # ndb.Key(urlsafe=kilpailu_id).get()
            if kilpailu is None:
                return make_response(render_template(u"virhe.html",virhe=u"Kilpailua ei löytynyt"),404)
        except:
            pass

    # Haetaan kilpailua.
    if request.method == 'GET':

        kilpailutForm = KilpailutForm()
        sarjat = []
        joukkueet = []
        rastit = []

        # Haetaan kilpailun sarjat, joukkueet ja jarjestetaan 
        # joukkueen jasenten nimet.
        try:
            formKilpailut = KilpailutForm(obj=kilpailu)
            sarjat = getSarjat(kilpailu_id)
            rastit = getRastit(kilpailu_id)
            for s in sarjat:
                joukkueet.append(getJoukkueet(s.key.urlsafe()))
            for x in joukkueet:
                for j in x:
                    j.jasenet.sort()
        except Exception as e:
            print e.message.encode("utf-8")
        return render_template('kilpailut.html',form=formKilpailut,kilpailuId=kilpailu_id,sarjat=sarjat,joukkueet=joukkueet,rastit=rastit)

    # Tehdaan jotain muuta kilpailulle.
    elif request.method == 'POST':

        formKilpailut = KilpailutForm(request.form)

        sarjat = []
        joukkueet = []
        rastit = []

        try:
            sarjat = getSarjat(kilpailu_id)
            rastit = getRastit(kilpailu_id)
            for s in sarjat:
                joukkueet.append(getJoukkueet(s.key.urlsafe()))
            for x in joukkueet:
                for j in x:
                    j.jasenet.sort()
        except:
            pass

        # Poistetaan kilpailu?
        try:
            request.form['poista']
            if delete_kilpailu(kilpailu_id):
                paluu_osoite = url_for(u"allKilpailut")
                return render_template('info.html',message=u"Kilpailu poistettu onnistuneesti.",paluu_osoite=paluu_osoite)
            else:
                return make_response(render_template(u"virhe.html",virhe="Virhe kilpailun poistossa."),500)
        except:
            pass

#        for i in request.form:
#            print i, request.form[i].encode('utf-8')

        # Formin tarkistus lapaisty.
        if formKilpailut.validate():

            old_kilpailu_id = kilpailu_id

            try:
                # Paivitetaan kilpailu ja id.
                k_id = updateKilpailu(kilpailu_id, formKilpailut)
                if k_id is not None:
                    kilpailu_id = k_id.urlsafe()
                    print u"kilpailu_id"
                    print unicode(kilpailu_id)

            # Paha virhe.
            except AssertionError as error:
                return make_response(render_template(u"virhe.html",virhe=error),500)

            # Virheita validoinnissa.
            except Exception as e:
                print e.message.encode("utf-8")
                return render_template('kilpailut.html',form=formKilpailut,kilpailuId=kilpailu_id,sarjat=sarjat,joukkueet=joukkueet,rastit=rastit)

            paluu_osoite = url_for(u"allKilpailut")
            if old_kilpailu_id == "0":
                return render_template('info.html',message=u"Kilpailu luotu onnistuneesti.",paluu_osoite=paluu_osoite)
            else:
                return render_template('info.html',message=u"Kilpailu muokattu onnistuneesti.",paluu_osoite=paluu_osoite)
        # TODO: onko turha?
        return render_template('kilpailut.html',form=formKilpailut,kilpailuId=kilpailu_id,sarjat=sarjat,joukkueet=joukkueet,rastit=rastit)

####################################################################################################

# Tulostaa yksittaisen sarjat. Tassa voi luoda/muokata/tuhota sarjan.
@app.route('/kilpailut/<kilpailu_id>/sarja/<sarja_id>', methods=['GET','POST'])
@bugTracker
@auth
def sarjat(kilpailu_id,sarja_id):

    sarja = Sarja()

    if sarja_id != "0":
        try:
            sarja = getSarja(sarja_id) # ndb.Key(urlsafe=kilpailu_id).get()
            if sarja is None:
                return make_response(render_template(u"virhe.html",virhe=u"Sarjaa ei löytynyt"),404)
        except:
            pass

    # Haetaan sarjaa.
    if request.method == 'GET':

        formSarjat = SarjatForm()
        joukkueet = []

        try:
            formSarjat = SarjatForm(obj=sarja)
            joukkueet = getJoukkueet(sarja_id)
            for j in joukkueet:
                j.jasenet.sort()
        except:
            pass
        return render_template('sarja.html',form=formSarjat,kilpailuId=kilpailu_id,sarja_id=sarja_id,joukkueet=joukkueet)

    # Tehdaan jotain muuta sarjalle.
    elif request.method == 'POST':

        formSarjat = SarjatForm(request.form)
        formSarjat.kilpailu = sarja.kilpailu
        joukkueet = []

        try:
            joukkueet = getJoukkueet(sarja_id)
            for j in joukkueet:
                j.jasenet.sort()
        except Exception as e:
            print e.message.encode("utf-8")

        try:
            request.form['poista']
            if delete_sarja(sarja_id): # TODO: toteuta
                paluu_osoite = url_for(u"kilpailut",kilpailu_id=kilpailu_id)
                return render_template('info.html',message=u"Sarja poistettu onnistuneesti.",paluu_osoite=paluu_osoite)
            else:
                return make_response(render_template(u"virhe.html",virhe="Virhe sarjan poistossa."),500)
        except:
            pass

        # Formin tarkistus lapaisty?
        if formSarjat.validate():

            old_sarja_id = sarja_id

            try:
                # Paivitetaan sarjat ja id.
                s_id = updateSarja(kilpailu_id,sarja_id, formSarjat)
                if s_id is not None:
                    sarja_id = s_id.urlsafe()

            # Paha virhe.
            except AssertionError as error:
                return make_response(render_template(u"virhe.html",virhe=error),500)

            # Virheita validoinnissa.
            except Exception as e:
                print e.message.encode("utf-8")
                return render_template('sarja.html',form=formSarjat,kilpailuId=kilpailu_id,sarja_id=sarja_id,joukkueet=joukkueet)
            paluu_osoite = url_for(u"kilpailut",kilpailu_id=kilpailu_id)
            if old_sarja_id == "0":
                return render_template('info.html',message=u"Sarja luotu onnistuneesti.",paluu_osoite=paluu_osoite)
            else:
                return render_template('info.html',message=u"Sarja muokattu onnistuneesti.",paluu_osoite=paluu_osoite)
        else:
            pass

        # TODO: onko turha?
        return render_template('sarja.html',form=formSarjat,kilpailuId=kilpailu_id,sarja_id=sarja_id,joukkueet=joukkueet)

####################################################################################################

# Tulostaa yksittaisen joukkueen. Tassa voi luoda/muokata/tuhota joukkueen.
@app.route('/kilpailut/<kilpailu_id>/sarja/<sarja_id>/joukkue/<joukkue_id>', methods=['GET','POST'])
@bugTracker
@auth
def joukkueet(kilpailu_id,sarja_id,joukkue_id):
    print u"joukkueet"
    joukkue = Joukkue()

    # Jasenien maksimilukumaara.
    max_jasen_lkm = 5

    # Luodaan dynaamisesti joukkue-form.
    class JoukkueetForm(JoukkueetBaseForm):

        # Validointi: uniikin jasen nimen tarkastus.
        def validate_jasen(form,field):
            nimet = []
            try:
                for k in range(max_jasen_lkm):
                    name = u"jasen" + unicode(k)
                    nimet.append(form[name].data)
            except Exception as e:
                print e.message.encode("utf-8")
            saman_nimiset = [x for x in nimet if x == field.data.strip()]
            if len(saman_nimiset) > 1:
                raise ValidationError(u"Nimi on jo käytössä.")

        # Validointi: tarkista onko sarjan nimi validi.
        def validate_sarja(form,field):

            # Tarkistetaan onko sarjan nimi olemassa tassa kilpailussa.
            if tarkistaSarjaNimi(kilpailu_id, "0", field.data.strip()):
                raise ValueError(u'Annettua sarjaa ei löydy kilpailusta.')

        # Fieldit.
        nimi = StringField('nimi',validators=[InputRequired(),validateName])
        sarja = StringField('sarja',validators=[InputRequired(),validate_sarja])

    # Luodaan jasen kentat.
    for i in range(max_jasen_lkm):
        name = u"jasen" + unicode(i)
        setattr(JoukkueetForm,name,StringField(name,validators=[validators.optional(),validateName,JoukkueetForm.validate_jasen]))

    # Jos url:ssa oleva joukkue_id eroaa nollasta. Yritetaan hakea ko.
    # joukkuetta.
    if joukkue_id != "0":
        try:
            joukkue = getJoukkue(joukkue_id)
            if joukkue is None:
                return make_response(render_template(u"virhe.html",virhe=u"Joukkuetta ei löytynyt"),404)
            if joukkue.rastileimaukset is None:
                joukkue.rastileimaukset = []
        except:
            pass

    # "Haetaan" joukkue.
    if request.method == 'GET':

        formJoukkueet = JoukkueetForm()
        rastit = []

        formJoukkueet = JoukkueetForm(obj=joukkue)

        sarja_nimi = u""
        try:
            formJoukkueet.sarja.process_data(getSarja(sarja_id).nimi)
            joukkue = getJoukkue(joukkue_id)

            # Turha?
            if joukkue.rastileimaukset is None:
                joukkue.rastileimaukset = []
                # ÖÖÖÖÖÖÖÖÖÖÖÖÖÖÖÖÖÖÖÖÖÖÖÖÖÖÖÖ
            rastit = [getRasti(j['rasti']) for j in joukkue.rastileimaukset]
            print u"RASTIT"

            print rastit
        except Exception as e:
            print e.message.encode("utf-8")

        # Asetetaan jasenien nimet.
        for i in range(max_jasen_lkm):
            name = u"jasen" + unicode(i)
            try:
                formJoukkueet[name].process_data(joukkue.jasenet[i]);
            except Exception as e:
                formJoukkueet[name].process_data(u"");
                print e.message.encode("utf-8")

        return render_template('joukkue.html',
                form=formJoukkueet,
                kilpailuId=kilpailu_id,
                sarja_id=sarja_id,
                joukkue_id=joukkue_id,
                joukkue=joukkue,
                rastit=rastit,
                max_jasen_lkm=max_jasen_lkm)

    # Luodaan, muokataan tai poistetaan joukkue.
    if request.method == 'POST':

        formJoukkueet = JoukkueetForm(request.form)
        #formSarjat.kilpailu = sarja.kilpailu
        rastit = []

        try:
            rastit = getRastit(kilpailu_id)
        except Exception as e:
            print e.message.encode("utf-8")

        try:
            request.form['poista']
            if delete_joukkue(joukkue_id): # TODO: toteuta rastien poisto

                paluu_osoite = url_for(u"kilpailut",kilpailu_id=kilpailu_id)
                return render_template('info.html',message=u"Joukkue poistettu onnistuneesti.",paluu_osoite=paluu_osoite)
            else:
                return make_response(render_template(u"virhe.html",virhe="Virhe joukkueen poistossa."),500)
        except:
            pass

        sarja_nimi = u""
        try:
            formJoukkueet.sarja.process_data(request.form['sarja'])

        except Exception as e:
            print e.message.encode("utf-8")

        # Formin tarkistus lapaisty?
        if formJoukkueet.validate():

            # Hakkerointia
            old_joukkue_id = joukkue_id

            try:
                # Paivitetaan joukkue ja id.
                j_id = updateJoukkue(kilpailu_id,sarja_id,joukkue_id,formJoukkueet,max_jasen_lkm) # TODO: Toteuta
                if j_id is not None:
                    # Nyt myos mahdollisesti sarja on muuttunut.
                    joukkue = getJoukkue(j_id.urlsafe())
                    sarja_id = joukkue.sarja.urlsafe()
                    joukkue_id = joukkue.key.urlsafe()

            # Paha virhe.
            except AssertionError as error:
                return make_response(render_template(u"virhe.html",virhe=error),500)

            # Virheita validoinnissa.
            except Exception as e:
                print e.message.encode("utf-8")
                return render_template('joukkue.html',form=formJoukkueet,
                        kilpailuId=kilpailu_id,
                        sarja_id=sarja_id,
                        joukkue_id=joukkue_id,
                        joukkue=joukkue,
                        rastit=rastit,
                        max_jasen_lkm=max_jasen_lkm)
            paluu_osoite = url_for(u"kilpailut",kilpailu_id=kilpailu_id)

            if old_joukkue_id == "0":
                return render_template('info.html',message=u"Joukkue luotu onnistuneesti.",paluu_osoite=paluu_osoite)
            else:
                return render_template('info.html',message=u"Joukkue muokattu onnistuneesti.",paluu_osoite=paluu_osoite)
        else:
            pass

    # TODO: onko turha?
    return render_template('joukkue.html',form=formJoukkueet,
            kilpailuId=kilpailu_id,
            sarja_id=sarja_id,
            joukkue_id=joukkue_id,
            joukkue=joukkue,
            rastit=rastit,
            max_jasen_lkm=max_jasen_lkm)

####################################################################################################

# Tyhjentaa koko tietokannan ja asettaa sinne alkuperaisen testitietokannan.
@app.route('/reset_database')
@bugTracker
@auth
def reset_database():

    # Poistetaan kaikki vanha.
    ndb.delete_multi(Joukkue.query().fetch(keys_only=True))
    ndb.delete_multi(Sarja.query().fetch(keys_only=True))
    ndb.delete_multi(Kilpailu.query().fetch(keys_only=True))
    ndb.delete_multi(Rasti.query().fetch(keys_only=True))

    kilpailut = initial_kilpailut()
    sarjat = initial_sarjat()
    joukkueet = initial_joukkueet()
    rastit = initial_rastit()

    kilpailu_entiteetit = []
    sarja_entiteetit = []
    joukkue_entiteetit = []
    rasti_entiteetit = []

    # Lisataan kilpailut.
    for k in kilpailut:
        kilpailu = Kilpailu(nimi=k['nimi'],
                            loppuaika=datetime.strptime(k['loppuaika'], "%Y-%m-%d %H:%M:%S"),
                            alkuaika=datetime.strptime(k['alkuaika'], "%Y-%m-%d %H:%M:%S"),
                            kesto=k['kesto'])
        kilpailu_entiteetit.append({'nimi':k['nimi'],'key':kilpailu.put()})
#        kilpailu_entiteetit.append(kilpailu)

    # Lisataan sarjat.
    for s in sarjat:
        # Tosielamassa epavarmaa. Saattaa tuottaa vanhentunutta tietoa. 
        # Pitaisi viela periaatteessa tarkistaa saatiinko kilpailu, mutta 
        # olkoon. Ei mene tuotantokayttoon.

        kilpailu = [x['key'] for x in kilpailu_entiteetit if x['nimi'] == s['kilpailu']]
        if len(kilpailu) == 0:
            raise ValueError(u"Ei loytynyt kilpailua nimella " + s['kilpailu'])
        sarja = Sarja(nimi=s['nimi'],
                      kilpailu=kilpailu[0],
                      kesto=s['kesto'])
        sarja_entiteetit.append({'nimi':s['nimi'],'key':sarja.put()})

        #sarja.put()

    # Lisataan joukkueet.
    for j in joukkueet:
        sarja = [x['key'] for x in sarja_entiteetit if x['nimi'] == j['sarja']]
        if len(sarja) == 0:
            raise ValueError(u"Ei loytynyt sarjaa nimella " + j['sarja'])
        try:
            joukkue = Joukkue(nimi=j['nimi'],
                              sarja=sarja[0],
                              jasenet=j['jasenet'])
            joukkue_entiteetit.append(joukkue)
        except Exception as e:
            print e.message.encode("utf-8")

    # Lisataan joukkueet yhdella rytinalla.
    ndb.put_multi(joukkue_entiteetit)

    # Lisataan rastit yhdella rytinalla.

    kintturogain = [x['key'] for x in kilpailu_entiteetit if x['nimi'] == u'Kintturogaining']
    for rasti in rastit:
        r = Rasti(lat=rasti['lat'],
                  lon=rasti['lon'],
                  koodi=rasti['koodi'],
                  kilpailu=kintturogain[0])
        rasti_entiteetit.append(r)

    ndb.put_multi(rasti_entiteetit)

    resp = make_response(u"Tietokanta asetettu lahtotilaan",200)
    resp.charset = "UTF-8"
    resp.mimetype = "text/plain"
    return resp

####################################################################################################

# Tulostaa yksittaisen kilpailun rastit. Tassa voi luoda/muokata/tuhota rastin.
@app.route('/kilpailut/<kilpailu_id>/rasti/<rasti_id>', methods=['GET','POST'])
@bugTracker
@auth
def rastit(kilpailu_id,rasti_id):
    rasti = Rasti()

    if rasti_id != "0":
        try:
            rasti = getRasti(rasti_id)
            if rasti is None:
                return make_response(render_template(u"virhe.html",virhe=u"Rastia ei löytynyt"),404)
        except:
            pass

    if request.method == 'GET':

        formRastit = RastitForm()

        try:
            formRastit = RastitForm(obj=rasti)
        except:
            pass
        return render_template('rasti.html',form=formRastit,kilpailuId=kilpailu_id,rasti_id=rasti_id)

    # Tehdaan jotain muuta rastille.
    elif request.method == 'POST':

        formRastit = RastitForm(request.form)

        try:
            request.form['poista']
            if delete_rasti(rasti_id): # Toteutettu?
                paluu_osoite = url_for(u"kilpailut",kilpailu_id=kilpailu_id)
                return render_template('info.html',message=u"Rasti poistettu onnistuneesti.",paluu_osoite=paluu_osoite)
            else:
                return make_response(render_template(u"virhe.html",virhe="Virhe rastin poistossa."),500)
        except:
            pass

        # Formin tarkistus lapaisty?
        if formRastit.validate():

            old_rasti_id = rasti_id

            try:
                # Paivitetaan rastit ja id.
                r_id = updateRasti(kilpailu_id,rasti_id, formRastit)
                if r_id is not None:
                    rasti_id = r_id.urlsafe()

            # Paha virhe.
            except AssertionError as error:
                return make_response(render_template(u"virhe.html",virhe=error),500)

            # Virheita validoinnissa.
            except Exception as e:
                print e.message.encode("utf-8")
                return render_template('rasti.html',form=formRastit,kilpailuId=kilpailu_id,rasti_id=rasti_id)

            paluu_osoite = url_for(u"kilpailut",kilpailu_id=kilpailu_id)
            if old_rasti_id == "0":
                return render_template('info.html',message=u"Rasti luotu onnistuneesti.",paluu_osoite=paluu_osoite)
            else:
                return render_template('info.html',message=u"Rasti muokattu onnistuneesti.",paluu_osoite=paluu_osoite)
        else:
            pass

        # TODO: onko turha?
        return render_template('rasti.html',form=formRastit,kilpailuId=kilpailu_id,rasti_id=rasti_id)

####################################################################################################

# Tulostaa yksittaisen rastileimaukset. Tassa voi luoda/muokata/tuhota
# rastileimauksen.
@app.route('/kilpailut/<kilpailu_id>/sarja/<sarja_id>/joukkue/<joukkue_id>/rastileimaus/<rastileimaus_id>', methods=['GET','POST'])
@bugTracker
@auth
def rastileimaukset(kilpailu_id,sarja_id,joukkue_id,rastileimaus_id):

    #class RastileimauksetForm(RastileimauksetBaseForm):
    #    aika = StringField('aika',validators=[InputRequired(),validateAika])
    #    rasti = KeyPropertyField(reference_class=Rasti,
    #            get_label=rasti_label,query=getRastitQuery(kilpailu_id))
        #rasti.query = getRastitQuery(kilpailu_id)

        #@classmethod
        #def rastiLeemaukset(cls,obj,query) -> 'RastileimauksetForm':
        #    rastiLeimaukset = Rastileimaukset()

    rastileimaus = RastiLeimaus()

    joukkue = getJoukkue(joukkue_id)

    if rastileimaus_id != "-1":
        try:
            # TODO: tarvitseeko tarkistaa indeksi?
            rastileimaus = joukkue.rastileimaukset[int(rastileimaus_id)]
        except:
            return make_response(render_template(u"virhe.html",virhe=u"Rastileimausta ei löytynyt"),404)

    # Yhteiset formit, seka GET etta POST metodille.
    formRastileimaukset = RastileimauksetForm()
    formRastileimaukset.rasti.query = getRastitQuery(kilpailu_id)

    if request.method == 'GET':

        #print getRasti(rastileimaus['rasti'])
        try:
            formRastileimaukset.aika.process_data(rastileimaus['aika'])
            formRastileimaukset.rasti.process_data(getRasti(rastileimaus['rasti']).key)
        except Exception as e:
            print e.message.encode('utf-8')
        return render_template('rastileimaus.html',
                form=formRastileimaukset,
                kilpailuId=kilpailu_id,
                sarja_id=sarja_id,
                joukkue_id=joukkue_id,
                rastileimaus_id=rastileimaus_id)

    # Tehdaan jotain muuta rastille.
    elif request.method == 'POST':

        #formTemp = RastileimauksetForm(request.form)

        ###formRastileimaukset = RastileimauksetForm(request.form)

        therasti = ndb.Key(Rasti,int(request.form['rasti'])).get()
        print therasti

        try:
            # TAMA EI PAIVITY JOS ESIM. paivamaara validation epaonnistuu.
            # Validointi ilmeisesti sotkee jostain syysta koodin selectionin.
            formRastileimaukset.rasti.process_data(therasti)
            formRastileimaukset.aika.process_data(request.form['aika'])

        except Exception as e:
            print e.message.encode('utf-8')

        try:
            request.form['poista']
            if delete_rastileimaus(joukkue_id,rastileimaus_id):
                paluu_osoite = url_for(u"joukkueet",kilpailu_id=kilpailu_id,sarja_id=sarja_id,joukkue_id=joukkue_id)
                return render_template('info.html',message=u"Rastileimaus poistettu onnistuneesti.",paluu_osoite=paluu_osoite)
            else:
                return make_response(render_template(u"virhe.html",virhe="Virhe rastileimaukset poistossa."),500)
        except:
            pass

        # Formin tarkistus lapaisty?
        if formRastileimaukset.validate():

            print formRastileimaukset.rasti.data.key.urlsafe()
            # Paivitetaan rastileimaus joukkueeseen.
            try:

                # Lisataan uusi rastileimaus.
                if rastileimaus_id == "-1":
                    if joukkue.rastileimaukset is None:
                        joukkue.rastileimaukset = []
                    joukkue.rastileimaukset.append({'aika':formRastileimaukset.aika.data, 'rasti': formRastileimaukset.rasti.data.key.urlsafe()})
                    joukkue.put()

                # Muokataan olemassa olevaa rastileimausta.
                else:
                    print unicode(rastileimaus_id)
                    rLeim_ID = int(rastileimaus_id)
                    joukkue.rastileimaukset[rLeim_ID]['aika'] = formRastileimaukset.aika.data
                    joukkue.rastileimaukset[rLeim_ID]['rasti'] = formRastileimaukset.rasti.data.key.urlsafe()
                    joukkue.put()

            # Paha virhe.
            except AssertionError as error:
                return make_response(render_template(u"virhe.html",virhe=error),500)

            # Virheita validoinnissa.
            except Exception as e:
                print e.message.encode("utf-8")
                return render_template('rastileimaus.html',
                        form=formRastileimaukset,
                        kilpailuId=kilpailu_id,
                        sarja_id=sarja_id,
                        joukkue_id=joukkue_id,
                        rastileimaus_id=rastileimaus_id)

            paluu_osoite = url_for(u"joukkueet",kilpailu_id=kilpailu_id,sarja_id=sarja_id,joukkue_id=joukkue_id)
            if rastileimaus_id == "-1":
                return render_template('info.html',message=u"Rastileimaus luotu onnistuneesti.",paluu_osoite=paluu_osoite)
            else:
                return render_template('info.html',message=u"Rastileimaus muokattu onnistuneesti.",paluu_osoite=paluu_osoite)

        # TODO: onko turha?
        return render_template('rastileimaus.html',
                form=formRastileimaukset,
                kilpailuId=kilpailu_id,
                sarja_id=sarja_id,
                joukkue_id=joukkue_id,
                rastileimaus_id=rastileimaus_id)
                #rastiID=rastiID)
