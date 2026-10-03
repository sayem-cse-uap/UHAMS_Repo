from django.contrib import admin

from ambulances.models import Ambulance

# Register your models here.
# Lets admins view/edit the ambulance fleet in the /admin/ site.
admin.site.register(Ambulance)
