from django.db import models
from UHAMS import settings

from core.models import User
# Create your models here.
class DriverProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    driver_license_number = models.CharField(max_length=255)
    shift_status = models.CharField(max_length=255)
    assigned_ambulance_ID = models.CharField(max_length=255)

    def acceptDispatch(self):
        pass

    def updateTripStatus(self):
        pass

    def toggleDutyStatus(self):
        pass

    def __str__(self):
        return f"{self.user.username} - {self.assigned_ambulance_ID}"