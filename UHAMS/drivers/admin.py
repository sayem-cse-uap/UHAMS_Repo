from django.contrib import admin

from drivers.models import DriverProfile

# Register your models here.
# Lets admins view/edit driver profiles in the /admin/ site.
admin.site.register(DriverProfile)
