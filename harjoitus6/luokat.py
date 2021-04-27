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

#########################
### Entity-luokat ym. ###
#########################

#####################################
### Entity validaattori-funktiot. ###
#####################################

def validate_kesto(prop, value):
    try:
        i = int(value)
    except ValueError:
        raise ValueError(u"Keston on oltava kokonaisluku")
    if not value > 0:
        raise ValueError(u"Keston on oltava suurempi kuin nolla")

def validate_time(prop, value):
    print "validoidaan aika"
    if isinstance(value,datetime): return None
    d = None
    try:
        d = datetime.strptime(value.strip(), "%Y-%m-%d %H:%M:%S")
    except:
        raise ValueError(u"Annettu aika ${0} ei ole muotota vvvv-kk-pp hh:mm:ss".format(value))
    return d

####################################
##         Kilpailu (Entity)      ##
####################################

class Kilpailu(ndb.Model):

    nimi = ndb.StringProperty(required=True)
    alkuaika = ndb.DateTimeProperty(required=True,validator=validate_time)
    loppuaika = ndb.DateTimeProperty(required=True,validator=validate_time)
    kesto = ndb.IntegerProperty(required=True, validator=validate_kesto)

    # ylimääritellään put-metodi. Lisätään tarkistus alku- ja loppuajalle
    def put(self, *args, **kwargs):
        if self.alkuaika > self.loppuaika:
            raise ValueError(u"Alkuajan on oltava pienempi kuin loppuajan")
        return self._put(*args, **kwargs)

####################################
##         Sarja (Entity)         ##
####################################

class Sarja(ndb.Model):
    def validate_kesto(prop, value):
        if not value > 0:
            raise ValueError(u"Keston on oltava suurempi kuin nolla")

    nimi = ndb.StringProperty(required=True)
    kesto = ndb.IntegerProperty(required=True, validator=validate_kesto)
    kilpailu = ndb.KeyProperty(required=True,kind=Kilpailu) #viittaus kilpailuun

####################################
##         Joukkue (Entity)       ##
####################################

class Joukkue(ndb.Model):
    def validate_jasenet(prop, value):
        jasenet = value
        if not len(jasenet) > 1:
                raise ValueError(u"Jäseniä on oltava vähintään kaksi : " + str(jasenet))
        if len(jasenet) > 5:
                raise ValueError(u"Jäseniä saa olla korkeintaan viisi : " + str(jasenet))

#    def validate_rastileimaukset(prop, value):
#        leimaukset = value
#
#        # Hae kilpailu.
#        kilpailu = getKilpailuByJoukkue(joukkue)


    nimi = ndb.StringProperty(required=True)
    # json-muotoon ja siitä purkaminen hoituu automaattisesti eli tähän kenttään voi suoraan tallentaa
    # melkein minkä tahansa pythonin listan, joka sisältää perustietotyyppejä
    jasenet = ndb.JsonProperty(required=True, validator=validate_jasenet)
    rastileimaukset = ndb.JsonProperty(default=[])
    sarja = ndb.KeyProperty(required=True,kind=Sarja) #viittaus sarjaan

#    # ylimääritellään put-metodi. Lisätään tarkistus etta vahintaan 
#    # kaksi jasenen nimea on annettu.
#    def put(self, *args, **kwargs):
#        if self.alkuaika > self.loppuaika:
#            raise ValueError(u"Alkuajan on oltava pienempi kuin loppuajan")
#        return self._put(*args, **kwargs)

####################################
##         Rasti (Entity)         ##
####################################

class Rasti(ndb.Model):
    def validate_latlon(prop, value):
        if value < -90.0 or value > 90.0:
            raise ValueError(u"Luvun täytyy olla välillä [-90.0,90.0].")

    def validate_koodi(prop, value):
        if len(value.strip()) == 0:
            raise ValueError(u"Koodi ei saa olla tyhjä merkkijono.")

    lat = ndb.FloatProperty(required=True, validator=validate_latlon)
    lon = ndb.FloatProperty(required=True, validator=validate_latlon)
    koodi = ndb.StringProperty(required=True, validator=validate_koodi)
    kilpailu = ndb.KeyProperty(required=True,kind=Kilpailu) #viittaus kilpailuun

####################################
##  Rastileimaus (Entity)         ##
####################################

class RastiLeimaus(ndb.Model):

    aika = ndb.DateTimeProperty(required=True) #,validator=validate_time)
    rasti = ndb.KeyProperty(kind=Rasti,required=True)

####################################
##         BaseFormit             ##
####################################

KilpailutBaseForm = model_form(Kilpailu, base_class=FlaskForm)
SarjatBaseForm = model_form(Sarja, base_class=FlaskForm, exclude=['kilpailu'])
JoukkueetBaseForm = model_form(Joukkue, base_class=FlaskForm, exclude=['sarja','jasenet'])
RastitBaseForm = model_form(Rasti, base_class=FlaskForm, exclude=['kilpailu'])
RastileimauksetBaseForm = model_form(RastiLeimaus, base_class=FlaskForm)

def kilpailu_label(kilpailu):
    return kilpailu.nimi

def rasti_label(rasti):
    return rasti.koodi

#####################################
## Formien validointi funktiot     ##
#####################################

def validateName(form, field):
    val = field.data.strip()
    if len(val) == 0:
        raise ValidationError(u"Kenttä ei saa olla tyhjä.")

def validateAika(form, field):
    val = field.data.strip()
    d = None
    try:
        d = datetime.strptime(val, "%Y-%m-%d %H:%M:%S")
    except:
        raise ValidationError(u"Annettu aika {0} ei ole muotota vvvv-kk-pp hh:mm:ss tai on muuten vain kelvoton.".format(val))
    return d

def validateKesto(form, field):
    val = field.data.strip()
    i = 0
    try:
        i = int(val)
    except ValueError:
        raise ValidationError(u"Keston on oltava kokonaisluku")
    if not i > 0:
        raise ValidationError(u"Keston on oltava suurempi kuin nolla")

# Ehka turha. Taman tarkistuksen voisi tehda ihan Entity-tasolla.
def validateLatLonForm(form, field):
    val = 0.0
    try:
        val = float(field.data.strip())
    except:
        raise ValidationError(u"Anna liukuluku.")

    if value < -90.0 or value > 90.0:
        raise ValueError(u"Luvun täytyy olla välillä [-90.0,90.0].")

## KESKEN
#def validate_koodi(form, field):
#    try:
#        val = float(field.data.strip())
#    except:
#        raise ValidationError(u"Anna liukuluku.")
#    return field
#
#    if value < -90.0 or value > 90.0:
#        raise ValueError(u"Luvun täytyy olla välillä [-90.0,90.0].")

####################################
##         KilpailuForm           ##
####################################

class KilpailutForm(KilpailutBaseForm):
    nimi = StringField('nimi',validators=[InputRequired(),validateName])
    alkuaika = StringField('alkuaika',validators=[InputRequired(),validateAika])
    loppuaika = StringField('loppuaika', validators=[InputRequired(),validateAika])
    kesto = StringField('kesto', validators=[InputRequired(),validateKesto])

####################################
##         SarjatForm             ##
####################################

class SarjatForm(SarjatBaseForm):
    nimi = StringField('nimi',validators=[InputRequired(),validateName])
    kesto = StringField('kesto', validators=[InputRequired(),validateKesto])

####################################
##         JoukkueetForm          ##
####################################

# Tama maaritellaan main.py:joukkueet funktiossa.

####################################
##         RastitForm             ##
####################################

class RastitForm(RastitBaseForm):
    koodi = StringField('nimi',validators=[InputRequired(),validateName])
    lat = FloatField('kesto', validators=[InputRequired(),validators.NumberRange(-90,90)])
    lon = FloatField('kesto', validators=[InputRequired(),validators.NumberRange(-90,90)])

####################################
##         RastitleimauForm       ##
####################################

class RastileimauksetForm(RastileimauksetBaseForm):
    aika = StringField('aika',validators=[InputRequired(),validateAika])
    rasti = KeyPropertyField(reference_class=Rasti, get_label=rasti_label) #, validate_koodi)
