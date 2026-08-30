from django.db import models
from django.contrib.auth.models import AbstractUser
# Create your models here.
class User(AbstractUser):
    # username, email, password already is in AbstractUser
    phone = models.CharField(max_length=20)

    class Meta:
        abstract = True

class Staff(User):
    role = models.CharField(max_length=255)
    availability_status = models.BooleanField(default=True)
    current_assignment = models.CharField(max_length=255)
    department = models.CharField(max_length=255)
    access_level = models.CharField(max_length=255)

    def allocateRoom(self):
        pass

    def dischargePatient(self):
        pass

    def manageSerialQueue(self):
        pass