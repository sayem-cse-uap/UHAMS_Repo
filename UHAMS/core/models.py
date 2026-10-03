"""
core.models - the one model that every other app hangs off: the User.

The project does not keep separate login tables for patients, doctors, drivers
and staff. Instead there is ONE user table (this model) holding everything
needed to log in, plus a `role` that says what kind of person it is. Each role
then has an optional "profile" in its own app that stores the role-specific
details:

    User (role=PATIENT) --1:1--> patients.PatientProfile
    User (role=DOCTOR)  --1:1--> doctors.DoctorProfile
    User (role=DRIVER)  --1:1--> drivers.DriverProfile
    User (role=STAFF)   --1:1--> staffs.StaffProfile

This is activated by AUTH_USER_MODEL = "core.User" in settings.py.
"""
from django.db import models
from django.contrib.auth.models import AbstractUser


# Create your models here.
class User(AbstractUser):
    """Custom user = Django's standard user (username, password, email, first/last name, ...)
    plus a role and a phone number."""

    class Role(models.TextChoices):
        """The four kinds of account. TextChoices gives us (database value, human label)
        pairs, so User.Role.STAFF == 'STAFF' in the database and "Staff" on screen."""
        STAFF = 'STAFF', 'Staff'
        DOCTOR = 'DOCTOR', 'Doctor'
        PATIENT = 'PATIENT', 'Patient'
        DRIVER = 'DRIVER', 'Driver'

    # Which kind of account this is. It decides which dashboard the user is sent
    # to after login (core/views.py) and which pages they may open
    # (core/decorators.py -> role_required). Defaults to PATIENT because that
    # is the account type anyone can create themselves.
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.PATIENT)

    # username, email, password already is in AbstractUser

    # Contact number. Not blank=True at the database level, but the settings
    # form (core/forms.py -> AccountForm) makes it optional and validates it.
    phone = models.CharField(max_length=20)
