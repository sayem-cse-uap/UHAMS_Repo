"""
ASGI config for UHAMS project.

ASGI is the modern async-capable interface between a web server and Django.
You do not need this file while developing with `runserver`; it matters when
you deploy with an ASGI server such as Uvicorn, Daphne or Hypercorn, e.g.:

    uvicorn UHAMS.asgi:application

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.1/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application

# Make sure Django knows which settings to use before building the app object.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'UHAMS.settings')

# The actual ASGI application object that the server calls for each request.
application = get_asgi_application()
