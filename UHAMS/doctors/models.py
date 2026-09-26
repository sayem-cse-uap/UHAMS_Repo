from django.db import models

# Create your models here.
from django.db import models
from UHAMS import settings

from core.models import User
# Create your models here.
class DoctorProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    specialization = models.CharField(max_length=255)
    licenseNumber = models.CharField(max_length=255)
    consultationFee = models.IntegerField()

    def updateSchedule(self):
        pass

    def viewAppointments(self):
        pass

    def prescribeMedication(self):
        pass

    def __str__(self):
        return f"{self.user.username} - {self.specialization}"