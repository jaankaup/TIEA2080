#!/usr/bin/python
# -*- coding: utf-8 -*-

# form accept-encoding="UTF-8"
import cgitb
import urllib2
import cgi
import os
from jinja2 import Template, Environment, FileSystemLoader

# Enabloidaan pythonin virheilmoitusten nakyminen selaimessa.
cgitb.enable()

# Tulostetaan html-protokollan vaatima mediatyyppi.
# Luodaan talla ohjelmalla css-tiedosto.
print u"""Content-type: text/css; charset=UTF-8\n""".encode("UTF-8")

# antaa polun alikansiossa olevaan jinja.html-tiedostoon:
# ei tarvitse huolehtia siitä onko polku riippuvainen
# palvelimenasetuksista
# os.environ['SCRIPT_FILENAME'] palauttaa polun suoritettavaan
# ohjelmaan (jinja.cgi)
# on syytä huomata, että tämä polku ei ole sama kuin
# tiedostopolku halava/jalava-palvelimissa
# os.path.dirname tipauttaa polusta muut kuin kansiot
# pois eli poistaa cgi-ohjelman lopusta
# os.path.join liittää os.path.dirnamen palauttaman
# polun ja 'templates' yhdeksi toimivaksi poluksi
# jos tätä haluaa kokeilla komentoriviltä niin
# tuloksena on keyerror.
# SCRIPT_FILENAME-ympäristömuuttuja löytyy
# vain www-palvelimen CGI-ympäristöstä eikä
# normaalista shellistä
try:
    tmpl_path = os.path.join(os.path.dirname(os.environ[u'SCRIPT_FILENAME']),u'templates')
except:
    # jos tänne päädytään www-palvelimessa niin koko sovellus kaatuu...
    tmpl_path = u"templates"

# alustetaan Jinja sopivilla asetuksilla
env = Environment(autoescape=True, loader=FileSystemLoader(tmpl_path), extensions=['jinja2.ext.autoescape'])

# ladataan oma template
template = env.get_template(u"vt2.css")

# Alustetaan lomake olio.
form = cgi.FieldStorage()

# foo on nyt ruudukon x-dimensio.
foo = form.getfirst(u"foo", u"8").decode("UTF-8")

try:
    foo = int(foo)
except:
    foo = 8

print template.render(foo=foo).encode("UTF-8")
