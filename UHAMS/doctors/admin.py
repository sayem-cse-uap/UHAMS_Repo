from django.contrib import admin

from doctors.models import DoctorProfile, TimeBlock

# Register your models here.
admin.site.register(DoctorProfile)
admin.site.register(TimeBlock)