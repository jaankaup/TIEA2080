#!/usr/bin/python
# -*- coding: utf-8 -*-

import logging
import urllib
import random
import inspect
import imp

logging.basicConfig(filename=u'../../../../flaskLog/flask.log', level=logging.DEBUG)

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

# Rakennta query. Ottaa argumenttina urlin ja dictin, ja muodostaa urlin jossa
# dictista muodostetty querysting.
def buildQuery(url,d):
    unurlencoded =  {}
    result = u""
    for k,v in d.iteritems():
        try:
            unurlencoded[k] = urllib.quote_plus(v)
        except Exception as e:
            try:
                unurlencoded[k] = urllib.quote_plus(v.encode("UTF-8"))
            except AttributeError as b:
                unurlencoded[k] = urllib.quote_plus(unicode(v).encode("UTF-8"))

    try:
        result = urllib.urlencode(unurlencoded)
    except Exception as e:
        debug(e)
    if len(result) > 0:
        return url + u"?" + result
    return url

###############################################################################

# Unquote funktio. Jos on jo dekoodattu, niin taytyy encoodata jotta voidaan 
# kutsua luotettavasti unquotea. Flaskia varten form.args.get....
def unQuoteInput(arg):
    result = u""
    if isinstance(arg,unicode):
        result = urllib.unquote_plus(arg.encode("UTF-8"))
    else:
        result = urllib.unquote_plus(arg)
    return result.decode('UTF-8')

###############################################################################
