from django.contrib import admin

from .models import Appointment

# Register your models here.
# Lets admins view/edit appointments in the /admin/ site.
admin.site.register(Appointment)
