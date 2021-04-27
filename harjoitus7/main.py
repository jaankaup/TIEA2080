# -*- coding: utf-8 -*-
from optparse import OptionParser
#import inspect
#import re
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
from rss import *
from misc import *

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
            exc_type, exc_value, exc_traceback = sys.exc_info()
            traceback.print_tb(exc_traceback,limit=10,file=sys.stdout)
            trace_result = traceback.extract_tb(exc_traceback,limit=10)
            #log(u"TRACE RESULT")
            #log(message=e.message)
            #error_msg = []
            #for x in trace_result:
            #    for y in x:
            #        if type(y) == int:
            #            error_msg.append(str(y))
            #            error_msg.append("\n")
            #        else:
            #            error_msg.append(y + " ")
            #log("".join(error_msg))
            log(e)
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
            login_url = users.create_login_url(url_for('allSyotteet'))
            greeting = '<a href="{}">Sign in</a>'.format(login_url)
        return '<html><body>{}</body></html>'.format(greeting)

####################################################################################################

@app.route('/info')
@bugTracker
#@auth
def info(message):
    return render_template('info.html',message=message)

####################################################################################################

# Tulostaa kaikki kilpailut.
@app.route('/syotteet', methods=['GET'])
@bugTracker
@auth
def allSyotteet():
    #syotteet = getRSS('http://www.hs.fi/rss/tuoreimmat.xml')
    syotteet = []
    uniikit_syotteet = []
    try:
        user = getRSS_user()

        # Jos olen koodannut oikein, linkkien pitaisi olla uniikit :).
        linkit = RSS_Link.query().fetch()

        # Kerataan tanne kaikki syotteet mutta siten, etta 
        # linkit ovat kaikki uniikkeja.
        for x in linkit:
            # Holmoa tehda tietokantakutsuja silmukassa, mutta menkoon nyt.
            uniikit_syotteet.append(RSS_Syote.query(RSS_Syote.link == x.key).fetch(1)[0])
        uniikit_syotteet.sort(key=lambda x: x.nimi)
        print uniikit_syotteet
        print str(len(uniikit_syotteet))

        # Taman kayttajan syotteet. Nyt sallitaan luonnollisesti myos
        # duplikaatti syotteet, silla muuten niita ei paase muokkaamaan
        # jarkevasti.
        syotteet = RSS_Syote.query(RSS_Syote.user == user.key).order(RSS_Syote.nimi).fetch()

        # Kaikkien kayttajien syotteet.
        #allSyotteet = RSS_Syote.query().order(RSS_Syote.nimi).fetch()

            #syotteet = RSS_Syote.query(encryptedID.IN(RSS_Sivu.userIDs))
    except Exception as e:
        log(e)
        #log(e.message)
        # TODO: ohjaa virhe sivulle
    return render_template('allSyotteet.html',syotteet=syotteet,allSyotteet=uniikit_syotteet)

####################################################################################################

# Tulostaa yksittaisen syotteen.
@app.route('/syotteet/<syote_id>', methods=['GET','POST'])
@bugTracker
@auth
def syotteet(syote_id):
    uutiset = []
    log(u"juhuuuu")
    paluu_osoite = url_for(u"allSyotteet")
    user = getRSS_user()

    # GET-METODI.
    if request.method == 'GET':
        syote = None
        if syote_id == u"0":
            syote = RSS_Syote()
            syote.user = user.key
        else:
            syote = getRSS_Syote(syote_id)

        # Jos syotetta ei loydy, niin ilmoitetaan siita.
        if syote is None:
            return render_template('info.html',message=u"Syötettä ei löydy.",paluu_osoite=paluu_osoite)

        form = None
        try:
            form = RSS_Syote_form(obj=syote)
            print u"YHHYYYYY"
            print syote.link is None
            linkkine = u""
            if syote.link is not None:
                linkkine = RSS_Link.query(RSS_Link.key == syote.link).fetch()[0].link
            form.link.process_data(linkkine)
        except Exception as e:
            log(e.message)
            paluu_osoite = url_for(u"allSyotteet")
            return render_template('info.html',message=u"Virhe syotteen haussa.",paluu_osoite=paluu_osoite)

        uutiset_suosikit = []
        suosikit = []
        try:
            # Hataratkaisu. Haetaan uutiset, ja totuus-lista, joka kertoo sen 
            # onko samassa indeksissa oleva uutinen suosikki vai ei.
            (uutiset_suosikit,uutiset) = getUutiset_suosikit(syote,form,user)
        except Exception as e:
            log(u"Nyt kyrvähti!")
            log(e.message)
            # TODO: ohjaa virhe sivulle
        return render_template('syote.html',form=form,uutiset=uutiset,us=uutiset_suosikit,syote_id=syote_id)

    # POST-METODI.
    if request.method == 'POST':
        form = None
        paluu_osoite = url_for(u"allSyotteet")

        # Rss syote formin poista nappula ruksittu.
        try:
            request.form['poista']
            if syote_id == u"0":
                return render_template('info.html',message=u"Poistetaan tallentamatonta rss-syötettä...",paluu_osoite=paluu_osoite)

            if delete_RSS_Syote(syote_id): #TODO: toteuta
                return render_template('info.html',message=u"Rss-syöte poistettu onnistuneesti.",paluu_osoite=paluu_osoite)
            else:
                return render_template('info.html',message=u"Virhe syotteen poistossa.",paluu_osoite=paluu_osoite)
        except:
            pass

        form = RSS_Syote_form(request.form)
        print request.form
        syote = None
        us = []
        uu = []
        if syote_id != u"0":
            syote = getRSS_Syote(syote_id)
            (uutiset_suosikit,uutiset) = getUutiset_suosikit(syote,form,user)
            us = uutiset_suosikit
            uu = uutiset

        # Formin tarkistus lapaisty?
        if form.validate():

            old_syote_id = syote_id


            try:
                s_id = updateSyote(syote_id, form)
                if s_id is not None:
                    syote_id = s_id.urlsafe()

            except ValueError as e:
                log(e)
                return render_template('info.html',message=u"Muokkaus kielletty. Et omista tätä syötettä.",paluu_osoite=paluu_osoite)

            except AssertionError as error:
                return render_template('syote.html',form=form,uutiset=uu,us=us,syote_id=syote_id)

            # Virheita validoinnissa.
            except Exception as error:
                log(error.message)
                return render_template('syote.html',form=form,uutiset=uu,us=us,syote_id=syote_id)

            if old_syote_id == "0":
                return render_template('info.html',message=u"Syote luotu onnistuneesti.",paluu_osoite=paluu_osoite)
            else:
                return render_template('info.html',message=u"Syote muokattu onnistuneesti.",paluu_osoite=paluu_osoite)
        else:
            pass

        # TODO: onko turha?
        return render_template('syote.html',form=form,uutiset=uu,us=us,syote_id=syote_id)


####################################################################################################
# Testi data. 
@app.route('/reset_database', methods=['GET'])
@bugTracker
#@auth
def reset_database():

    # Tuhotaan tietokannan sisalto.
    ndb.delete_multi(RSS_Syote.query().fetch(keys_only=True))
    ndb.delete_multi(RSS_User.query().fetch(keys_only=True))
    ndb.delete_multi(RSS_Uutinen.query().fetch(keys_only=True))
    #ndb.delete_multi(RSS_Suosikki.query().fetch(keys_only=True))
    ndb.delete_multi(RSS_Link.query().fetch(keys_only=True))

    userID = encrypt('185804764220139124118')

    # Testi_kayttaja
    user = RSS_User(userID=userID.decode('iso-8859-1'))
    user_id = user.put()

    #user = User(userID=userID.decode('iso-8859-1'))
    #user = User(userID=userID)
    # Linkit
    links = []
    links.append(RSS_Link(link=u"https://www.hs.fi/rss/tuoreimmat.xml").put())
    links.append(RSS_Link(link=u"https://feeds.yle.fi/uutiset/v1/recent.rss?publisherIds=YLE_UUTISET").put())
    links.append(RSS_Link(link=u"https://feeds.yle.fi/uutiset/v1/mostRead/YLE_UUTISET.rss").put())
    links.append(RSS_Link(link=u"https://www.kela.fi/ajankohtaista/-/asset_publisher/mHBZ5fHNro4S/rss").put())
    links.append(RSS_Link(link=u"https://www.is.fi/rss/digitoday.xml").put())
    links.append(RSS_Link(link=u"http://lifehacker.com/rss").put())
    links.append(RSS_Link(link=u"http://www.neatorama.com/feed").put())
    links.append(RSS_Link(link=u"http://endorfiininmetsastaja.fi/feed/").put())


    # Syotteet
    syotteet = []
    syotteet.append(RSS_Syote(nimi=u"HS",
            link=links[0],
            user=user_id))
    syotteet.append(RSS_Syote(nimi=u"Yle1",
            link=links[1],
            user=user_id))
    syotteet.append(RSS_Syote(nimi=u"Yle2",
            link=links[2],
            user=user_id))
    syotteet.append(RSS_Syote(nimi=u"Kela",
            link=links[3],
            user=user_id))
    syotteet.append(RSS_Syote(nimi=u"Digitoday",
            link=links[4],
            user=user_id))
    syotteet.append(RSS_Syote(nimi=u"Life",
            link=links[5],
            user=user_id))
    syotteet.append(RSS_Syote(nimi=u"Neatorama",
            link=links[6],
            user=user_id))
    syotteet.append(RSS_Syote(nimi=u"endorfiininmetsastaja",
            link=links[7],
            user=user_id))

    ndb.put_multi(syotteet)
    #s.put()
    #syotteet.append(s)
    # To data.encode('iso-8859-1')

    return redirect(url_for(u'allSyotteet'))

####################################################################################################

# Laitetaan sitten tannekin tuo PUT.
@app.route('/suosikit', methods=['GET','PUT'])
@bugTracker
@auth
def suosikit():

    user = getRSS_user()

    if request.method == 'GET':
        #uutis_keyt = [x.uutinen for x in getSuosikit()]
        uutis_keyt = [ndb.Key(urlsafe=x['uutinen']) for x in user.suosikit]
        uutiset = []
        if len(uutis_keyt) > 0:
            uutiset = RSS_Uutinen.query(RSS_Uutinen.key.IN(uutis_keyt)).fetch()
        return render_template("suosikit.html", uutiset=uutiset)

    # PUT-METODI. Ajax-kutstu (suosikit ym. tahan). Huonoa suunnittelua.
    if request.method == 'PUT':
        data = request.data;
        try:
            data = json.loads(data)
        except Exception as e:
            log(e.message)
            log(e)
            return make_response(u"onkelimia juu",500)
        tags = [u"link",u"description",u"title"]

        # Kaydaan lapi lista suosikkeja.

        command = data['command']
        print command

        # Jarjestetaan suosikit uudestaan.
        if command == u"UPDATE":

            # Kloonataan suosikit.
            #temp_suosikit = json.loads(json.dumps(user.suosikit))
            uusi_jarjestys = []
            del user.suosikit[:]

            for z in data['data']:
                for x in z:
                    if x not in tags:
                        log(x + u" ei loydy!!!")
                        return make_response(u"Taytyy olla attribuutti: " + x,500)
                u = RSS_Uutinen.query(RSS_Uutinen.link == z['link']).fetch()
                try:
                    user.suosikit.append({u"uutinen": u[0].key.urlsafe()})
                    #uusi_jarjestys.append({u"uutinen": u[0].key.urlsafe()})
                except Exception as e:
                    log("suosikit:put:update: ei loytynyt uutista!")
                    log(e)
                #user.suosikit = uusi_jarjestys

        # Luodaan uusi tai tuhotaan suosikki.
        else:
            for z in data['data']:
                for x in z:
                    if x not in tags:
                        log(x + u" ei loydy!!!")
                        return make_response(u"Taytyy olla attribuutti: " + x,500)
                try:
                    print u"2"
                    # Ajaxista tuli uusi suosikki. Lisataan se talle kayttajalle.
                    if command == u"NEW":
                        old_uutinen = RSS_Uutinen.query(RSS_Uutinen.link == z['link']).fetch()

                        # Luodaan uusi uutinen.
                        if (len(old_uutinen) == 0):
                            uutinen = RSS_Uutinen(title=z['title'],description=z['description'],link=z['link'])
                            uutinen_key = uutinen.put()
                            suosikki = {u"uutinen":uutinen_key.urlsafe()}
                            user.suosikit.insert(0,suosikki)

                        # Kaytetaan jo entuudestaan tallennetua uutista.
                        else:
                            suosikki = {u"uutinen":old_uutinen[0].key.urlsafe()}
                            user.suosikit.insert(0,suosikki)

                    # Poistetaan suosikeista uutinen.
                    elif command == u"DELETE":
                        uutinen = None
                        try:
                            uutinen = RSS_Uutinen.query(RSS_Uutinen.link == z['link']).fetch()[0].key.urlsafe()
                        except Exception as e:
                            log(e)
                        for i in range(len(user.suosikit)):
                            if user.suosikit[i]['uutinen'] == uutinen:
                                del user.suosikit[i]
                                break

                except Exception as e:
                    log(e)
                    return make_response(unicode(e.message.encode),500)
    try:
        user.put()
    except Exception as e:
        log(e)
    return make_response(u"oolrait",200)
