"""
WSGI config for UHAMS project.

WSGI is the classic synchronous interface between a web server and Django.
Production servers such as Gunicorn or uWSGI import this module and call the
``application`` object for every request, e.g.:

    gunicorn UHAMS.wsgi:application

It exposes the WSGI callable as a module-level variable named ``application``.
(``settings.WSGI_APPLICATION`` points at it, and `runserver` uses it too.)

For more information on this file, see
https://docs.djangoproject.com/en/6.1/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

# Make sure Django knows which settings to use before building the app object.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'UHAMS.settings')

# The actual WSGI application object that the server calls for each request.
application = get_wsgi_application()
