from django.contrib import admin
from patients.models import PatientProfile

# Register your models here.
# Lets admins view/edit patient profiles in the /admin/ site.
admin.site.register(PatientProfile)
