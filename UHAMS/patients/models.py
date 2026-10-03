"""patients.models - the patient's own details, attached to a core.User with role=PATIENT."""
from django.db import models
# Note: this imports the project's settings *module* directly (rather than
# `from django.conf import settings`). It works because only AUTH_USER_MODEL,
# a plain string, is read from it.
from UHAMS import settings

class PatientProfile(models.Model):
    # One profile per login account; deleting the user also deletes the profile.
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    bloodGroup = models.CharField(max_length=100)          # e.g. "O+"
    emergencyContact = models.CharField(max_length=100)    # who to call in an emergency
    # The staff member (nurse, receptionist, ...) responsible for this patient.
    # Referenced by the string "staffs.StaffProfile" to avoid a circular import.
    # SET_NULL: if that staff profile is deleted the patient simply becomes unassigned.
    # related_name="patients" gives StaffProfile its `.patients` list.
    assigned_staff = models.ForeignKey("staffs.StaffProfile", on_delete=models.SET_NULL, null=True, blank=True, related_name="patients")

    def __str__(self):
        return f"{self.user.username} - {self.bloodGroup}"
