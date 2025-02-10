# -*- coding: utf-8 -*-
"""
    APP start-up configuration
"""
import locale
import os
import sys

from django.core.wsgi import get_wsgi_application

locale.setlocale(locale.LC_ALL, 'cs_CZ.utf-8')

APACHE_CONFIGURATION = os.path.dirname(__file__)
PROJECT = os.path.dirname(APACHE_CONFIGURATION)
WORKSPACE = os.path.dirname(PROJECT)
sys.path.append(WORKSPACE)

# Pokud se settings nachazi v /srv/app/moje_aplikace,
# bude obsah pro DJANGO_SETTINGS_MODULE: moje_aplikace.settings
os.environ.setdefault("DJANGO_SETTINGS_MODULE", 'StockWise.settings')

application = get_wsgi_application()
