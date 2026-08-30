from django.db import models
from UHAMS import settings

from core.models import User
# Create your models here.
class StaffProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    availability_status = models.BooleanField(default=True)
    current_assignment = models.CharField(max_length=255, blank=True)
    department = models.CharField(max_length=255)
    access_level = models.CharField(max_length=255)

    def allocateRoom(self):
        pass

    def dischargePatient(self):
        pass

    def manageSerialQueue(self):
        pass

    def __str__(self):
        return f"{self.user.username} - {self.department}"