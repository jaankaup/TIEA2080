# -*- coding: utf-8 -*-

import inspect
import hashlib
import json
from google.appengine.api import urlfetch

# APUFUNKTIOITA

#########################################################################

# Lahetetaan parametrina annettu message slackkiin. Talla tavalla saan 
# kenties virheilmoitukset ym. paremmin haltuun kun sovellus pyorii pilvessa.
def websoc(message):
    END_POINT = u"https://slack.com/api/chat.postMessage"
    headers = {u"Content-type": u"application/json", u"Authorization": u"Bearer tahan tulee tokeni"}
    data = json.dumps({u"channel": u"CKB3VNYP7", u"text":message, u"name":u"janne.a.kauppinen"})
    rpc = urlfetch.create_rpc()
    try:
        urlfetch.make_fetch_call(rpc, url=END_POINT, payload=data, method=urlfetch.POST, headers=headers)
        result = rpc.get_result()
        print result.content
    except Exception as e:
        print e.message.encode('utf-8')

#########################################################################

# Logitus funktio. Tulostaa nyt viestin vain slackiin.
def log(message,level=1):
    msg = myEncode(message=message,level=level+1)
    #if type(message) == str:
    #   msg = myEncode(message)
    #elif type(message) == unicode:
    #   msg = message
    #else:
    #    msg = str(message)
    print msg # Konsoli
    #websoc(message) # Slack

    # Nait ei voi kayttaa silla valittaa etta toimii interpreretin paalla.
    # Pitaisi olla mainissa jotta saikeistys toimii...
    #pool = Pool(processes=1)
    #result = pool.apply_async(websoc,(message,))

############################################################

# Encoodaa merkkijonon unicodeksi ja lisaa siihen tiedon mista tulostus
# tehtiin.
def myEncode(message,level=1):
    #print "the type is:" + str(type(message))
    if not (type(message) == str or type(message) == unicode):
        return message
    if type(message) == unicode:
        message = message.encode('utf-8')
    decoded_msg = None
    #if type(message) == unicode:
    #    message = message.encode('utf-8')
    stack = inspect.stack()
    try:
        decoded_msg = "{0}:{1}:{2}=> {3}\n".format(stack[level][1], stack[level][2], stack[level][3], message)
    except UnicodeDecodeError:
        decoded_msg = "{0}:{1}:{2}=> {3}\n".format(stack[level][1], stack[level][2], stack[level][3], message)
    except Exception as e:
        print u"myEncode:"
        return e.message.encode('utf-8')
    return decoded_msg

############################################################

# Apufunktio joka tulostaa olion tyypin, metodit ja attribuutit.
def objectInfo(obj):

    obj_type = u""
    obj_methods = []
    obj_attributes = []

    if obj is None:
        obj_type = u"None"
    else:
        obj_type = u"Type == " + unicode(type(obj))
        print obj_type

    # Metodit.
    if obj is not None:
        obj_methods = [m_name for m_name in dir(obj) if callable(getattr(obj, m_name))]

    # Attribuutit (muut).
    if obj is not None:
        obj_attributes = [m_name for m_name in dir(obj) if not callable(getattr(obj, m_name))]

    print u"Object type:"
    print obj_type
    print u""
    print u"Object methods:"
    print obj_methods
    print u""
    print u"Object attributes:"
    print obj_attributes
    print u""

############################################################

def encrypt(userID):
    token = hashlib.sha512()
    try:
        token.update("erkkiajaamopolla")
        token.update(userID)
    except Exception as e:
        log(e)
    return token.digest()

############################################################

# TURHA?
def checkUserId(userID):
    userID_digest = encrypt(userID)
    digest = u"EY\x9d\xc5\x9f\xa1\x91\xbd\x90\xcfEu\xe8\x84,\xa5\x9a\xf6:\xa2\x11>\xee\xe2\xf6\x9c\xa1\xf2>\xeaK\x9dQF\x82\xcc\xbap\xf8A\x13\xe3\xb2lF\xcc\x9cG\xd3\xce\xabq,e\xe6\xff\xb0\x80\x14\x9e\xc7U>\xa0"
    return userID_digest == digest
