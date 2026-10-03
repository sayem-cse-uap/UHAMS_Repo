"""doctors.models - the doctor's profile and the weekly time blocks they work in."""
from django.db import models
from UHAMS import settings


class DoctorProfile(models.Model):
    # One profile per login account (a core.User with role=DOCTOR).
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    specialization = models.CharField(max_length=255)   # e.g. "Cardiology"
    licenseNumber = models.CharField(max_length=255)    # medical licence; read-only after registration
    consultationFee = models.IntegerField()             # whole currency units

    def __str__(self):
        return f"{self.user.username} - {self.specialization}"

class TimeBlock(models.Model):
    """A repeating weekly slot, e.g. "Mondays 09:00-12:00". Not tied to a calendar
    date: the date is only chosen when an appointment is confirmed."""
    class DayOfWeek(models.IntegerChoices):
        # The numbers match Python's date.isoweekday() (Monday=1 ... Sunday=7),
        # which is how appointments.forms.AppointmentConfirmForm compares a
        # chosen date to a block's day.
        MONDAY = 1, 'Monday'
        TUESDAY = 2, 'Tuesday'
        WEDNESDAY = 3, 'Wednesday'
        THURSDAY = 4, 'Thursday'
        FRIDAY = 5, 'Friday'
        SATURDAY = 6, 'Saturday'
        SUNDAY = 7, 'Sunday'
    # Deleting a doctor deletes their time blocks too.
    doctor = models.ForeignKey(DoctorProfile, on_delete=models.CASCADE)
    day = models.IntegerField(choices=DayOfWeek.choices)
    start_time = models.TimeField()
    end_time = models.TimeField()

    def __str__(self):
        return f"{self.doctor.user.username} : {self.start_time} - {self.end_time}"
