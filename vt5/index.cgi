#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys
from wsgiref.handlers import CGIHandler
from werkzeug.debug import DebuggedApplication

try:
    # oma on oman python-tiedoston nimi. esim. tässä tapauksessa oma.py
    # tiedostossa on oltava Flask-sovellus
    from ht5 import app as application
except:
    print "Content-Type: text/plain;charset=UTF-8\n"
    print "Syntaksivirhe:\n"
    for err in sys.exc_info():
        print err

if __name__ == '__main__':
    handler = CGIHandler()
    handler.run(DebuggedApplication(application))
