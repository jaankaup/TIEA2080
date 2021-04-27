# -*- coding: utf-8 -*-

from flask import Flask, render_template, request, make_response, redirect, url_for
from google.appengine.ext import ndb
from wtforms_appengine.ndb import model_form
from wtforms_appengine.fields import KeyPropertyField
from flask_wtf import FlaskForm
from wtforms import SelectField, HiddenField, StringField, ValidationError, FloatField
from wtforms.validators import InputRequired
from wtforms import validators
from datetime import datetime
from google.appengine.api import users
from misc import *

from xml.dom.minidom import parse
import urllib
import sys

############################################################

def non_empty(prop, value):
    if len(value.strip()) == 0:
        raise ValueError(u"Ei saa olla tyhjä.")

############################################################

#############################
### RSS_User luokka       ###
#############################

class RSS_User(ndb.Model):
    userID = ndb.StringProperty(required=True)
    suosikit = ndb.JsonProperty(required=True,default=[])

#############################
### RSS_Syote luokka      ###
#############################

class RSS_Syote(ndb.Model):
#    title = ndb.StringProperty(required=True, validator=non_empty)
#    description = ndb.StringProperty(required=True, validator=non_empty)
    nimi = ndb.StringProperty(required=True, validator=non_empty)
    link = ndb.KeyProperty(required=True)
    user = ndb.KeyProperty(required=True)
    #suosikit = ndb.JsonProperty(default=[])

    # ylimääritellään put-metodi.
#    def put(self, *args, **kwargs):
#        #link = None
#        #doc = None
#        try:
#            link = urllib.urlopen(self.link)
#        except:
#            raise ValueError(u"Annettu linkki ei ole kelvollinen.")
#        try:
#            doc = parse(link)
#        except:
#            raise ValueError(u"Dokumenttia ei voi jäsentää.")
#        if len(doc.getElementsByTagName(u"rss")) == 0:
#            raise ValueError(u"Dokumentista ei löydy rss-elementtiä.")
#        if len(RSS_Syote.query(ndb.OR(RSS_Syote.nimi == self.nimi, RSS_Syote.link == self.link)).fetch()) > 0:
#            raise ValueError(u"Nimi tai linkki on jo tallennettu.")
#
#        return self._put(*args, **kwargs)

#############################
### RSS_Link luokka       ###
#############################

class RSS_Link(ndb.Model):
    link = ndb.StringProperty(required=True, validator=non_empty)

    # ylimääritellään put-metodi.
    # Tarkistetaan onko sivu olemassa.
    # Tarkistetaan onko sivulla rss.
    # Tarkistetaan onko vastaavanlainen jo tallennettu.
    def put(self, *args, **kwargs):
        link = None
        doc = None
        try:
            link = urllib.urlopen(self.link)
        except:
            raise ValueError(u"Annettu linkki ei ole kelvollinen.")
        try:
            doc = parse(link)
        except:
            raise ValueError(u"Dokumenttia ei voi jäsentää.")
        # Jos sivulta ei loydy rss tai channel elementtia, niin...
        if not (len(doc.getElementsByTagName(u"rss")) != 0 or len(doc.getElementsByTagName(u"channel")) != 0):
            raise ValueError(u"Dokumentista ei löydy rss tai channel elementtiä.")
        if len(RSS_Syote.query(RSS_Link.link == self.link).fetch()) > 0:
            raise ValueError(u"Linkki on jo tallennettu.")

        return self._put(*args, **kwargs)

#############################
### RSS_Uutinen luokka    ###
#############################

class RSS_Uutinen(ndb.Model):
    title = ndb.StringProperty(required=True, validator=non_empty)
    description = ndb.TextProperty(required=True, validator=non_empty)
    link = ndb.StringProperty(required=True, validator=non_empty)
    #suosikki = ndb.StringProperty(required=True, default=u"DELETE")

#############################
### RSS_Suosikki          ###
#############################

#class RSS_Suosikki(ndb.Model):
#    #user = ndb.KeyProperty(required=True)
#    uutinen = ndb.StringProperty(required=True)
#    #order = ndb.IntegerProperty(required=True,default=0)

####################################
##         BaseFormit             ##
####################################

SyoteBaseForm = model_form(RSS_Syote, base_class=FlaskForm, exclude=['user','link'])

####################################
##         Form-validaattorit     ##
####################################

def form_noempty(form, field):
    val = field.data.strip()
    if len(val) == 0:
        raise ValidationError(u"Kenttä ei saa olla tyhjä.")

####################################
##         RSS_Syote_form         ##
####################################

class RSS_Syote_form(SyoteBaseForm):
    nimi = StringField('nimi',validators=[InputRequired(),form_noempty])
    link = StringField('link',validators=[InputRequired(),form_noempty])

#############################
### rss funktiot          ###
#############################

############################################################

def getRSS(url):

    try:
        doc = parse(urllib.urlopen(url))
        uutiset = createRSS_uutiset(doc)
        return uutiset

    except Exception as ex:
        log(ex.message)
        for e in sys.exc_info():
            print e

############################################################

def getData(node):

    try:
        if node.firstChild.nodeName == "#cdata-section":
            return node.firstChild.data #.encode('utf-8')
        else:
            return node.firstChild.nodeValue #.encode('utf-8')
    except Exception as e:
        pass

############################################################

# Parsii dokumentista uutiset, tsekkaa onko kayttajalla niissa 
# suosikkeja. Palauttaa listan loydetyista uutisista.
def createRSS_uutiset(doc):

    items = doc.getElementsByTagName(u"item")

    uutiset = []
    laskuri = 0

    user = getRSS_user()

    for i in items:
        title = ""
        description = ""
        link = ""

        for j in i.childNodes:
            try:
                if j.tagName == u"description":
                    description = getData(j)
                if j.tagName == u"title":
                    title = getData(j)
                if j.tagName == u"link":
                    link = getData(j)
            except Exception as e:
                continue
        try:
            uutinen = RSS_Uutinen(title=title,description=description,link=link)#,suosikki="DELETE")
            uutiset.append(uutinen)
        except Exception as e:
            log(e.message)
            pass
    return uutiset

############################################################

# Hakee taman hetkisen kayttajan RSS_User instanssin. 
# Jos kayttaja on uusi, niin luodaan se tassa.
def getRSS_user():

    try:
        userID = users.get_current_user().user_id()
        encryptedID = encrypt(userID).decode('iso-8859-1')

        rss_user = RSS_User.query(RSS_User.userID == encryptedID).fetch()

        # Uusi kayttaja.
        if len(rss_user) == 0:
            user = RSS_User(userID=userID.decode('iso-8859-1'))
            user_id = user.put()
            return ndb.Key(urlsafe=user_id.urlsafe()).get()
        else:
            return rss_user[0]

    except Exception as e:
        log(e)

######################################################################################################


# Paivittaa kilpailun annetusta kilpailuFormista. 
# Asettaa kilpailuFormiin mahdolliset virheet.
# Luottaa siihen etta lomakkeen validoinnit ovat suoritettu.
def updateSyote(syote_id, form):

    syote = None

    # Jos ollaan muokkaamassa olemassa olevaa joukkuetta. 
    if (syote_id != '0'):
        syote = getRSS_Syote(syote_id)
        user = getRSS_user()
        if (syote.user != user.key):
            raise ValueError(u"Et voi muokata tätä syötettä. Et omista sitä.")
        assert syote is not None, u"updateSyote: Syotetta " + syote_id + " ei loydy."

    if syote is None:
        syote = RSS_Syote()

    try:
        syote.nimi = form.nimi.data.strip()
    except Exception as e:
        raise AssertionError(u"updateSyote: syote.nimi epannoistui.'" + unicode(e) + "'.")

    linkki = form.link.data.strip()
    log(u"1234123412341432")
    log(linkki)
    link = RSS_Link.query(RSS_Link.link == linkki).fetch()
    print link

    # Luodaan uusi linkki.
    if len(link) == 0:
        newLink = None
        try:
            newLink = RSS_Link(link=linkki).put()
            syote.link = newLink.key
        except ValueError as e:
            form.link.errors.append(unicode(e))
            raise Exception(unicode(e))
    else:
        syote.link = link[0].key

    try:
        log(u"tallennetaan syote")
        syote.user = getRSS_user().key
        return syote.put()
    except ValueError as e:
        raise Exception(unicode(e))

####################################################################################################

# Etsii tietokannasta kilpailun id:n perusteella.
def getRSS_Syote(syote_id):
    try:
        return ndb.Key(urlsafe=syote_id).get()
    except Exception as e:
        log(e.message)

####################################################################################################

def delete_RSS_Syote(syote_id):
    syote = getRSS_Syote(syote_id)
    if syote is None:
        return False
    try:
        syote.key.delete()
    except Exception as e:
        log(e)
        return False
    return True

####################################################################################################

def getSuosikit():

    user = getRSS_user()
    suosikit = RSS_Suosikki.query(RSS_Suosikki.user == user.key).fetch()
    return suosikit

####################################################################################################

def getUutiset_suosikit(syote,form,user):
    uutis_link = ndb.Key(urlsafe=syote.link.urlsafe()).get().link
    uutiset = getRSS(uutis_link)
    suosikit_uutiset_keyt = [ndb.Key(urlsafe=x['uutinen']) for x in user.suosikit]
    suosikki_uutiset = []
    if len(suosikit_uutiset_keyt) > 0:
        suosikki_uutiset = RSS_Uutinen.query(RSS_Uutinen.key.IN(suosikit_uutiset_keyt)).fetch()
    linkit = [x.link for x in suosikki_uutiset]
    #form.link.process_data(uutis_link)
    return ([x.link in linkit for x in uutiset],uutiset)
