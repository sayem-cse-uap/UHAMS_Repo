from django.db import models
from django.contrib.auth.models import AbstractUser
# Create your models here.
class User(AbstractUser):
    class Role(models.TextChoices):
        STAFF = 'STAFF', 'Staff'
        DOCTOR = 'DOCTOR', 'Doctor'
        PATIENT = 'PATIENT', 'Patient'
        DRIVER = 'DRIVER', 'Driver'

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.PATIENT)

    # username, email, password already is in AbstractUser
    phone = models.CharField(max_length=20)

class StaffUser(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
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

    def __ster__(self):
        return f"{self.user.username} - {self.department}"