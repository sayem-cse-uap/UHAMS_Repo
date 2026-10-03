"""drivers.models - the ambulance driver's profile (a core.User with role=DRIVER)."""
from django.db import models
from UHAMS import settings


class DriverProfile(models.Model):
    # One profile per login account; deleting the user also deletes the profile.
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    driver_license_number = models.CharField(max_length=255)
    shift_status = models.CharField(max_length=255)   # free text, e.g. "Day shift"; the driver can edit it
    # The human-readable ID (e.g. "AMB-001") of the driver's ambulance. This is a
    # COPY: the real link is Ambulance.driver (see ambulances/models.py), and
    # Ambulance.save() keeps this text in sync automatically. Reverse access
    # from here to the real ambulance is `driver_profile.ambulance`.
    assigned_ambulance_ID = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.user.username} - {self.assigned_ambulance_ID}"
