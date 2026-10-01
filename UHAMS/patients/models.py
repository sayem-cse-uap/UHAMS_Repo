from django.db import models
from UHAMS import settings

from core.models import User
# Create your models here.
class PatientProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    bloodGroup = models.CharField(max_length=100)
    emergencyContact = models.CharField(max_length=100)

    def bookAppointment(self):
        pass

    def requestAmbulence(self):
        pass

    def __str__(self):
        return f"{self.user.username} - {self.bloodGroup}"