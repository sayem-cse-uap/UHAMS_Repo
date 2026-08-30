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