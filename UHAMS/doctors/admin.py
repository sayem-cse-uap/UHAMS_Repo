from django.contrib import admin

from doctors.models import DoctorProfile, TimeBlock

# Register your models here.
# Lets admins view/edit doctors and their weekly time blocks in /admin/.
admin.site.register(DoctorProfile)
admin.site.register(TimeBlock)
