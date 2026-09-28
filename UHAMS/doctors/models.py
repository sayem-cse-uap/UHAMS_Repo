from django.db import models

# Create your models here.
from django.db import models
from UHAMS import settings

from core.models import User
# Create your models here.
class DoctorProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    specialization = models.CharField(max_length=255)
    licenseNumber = models.CharField(max_length=255)
    consultationFee = models.IntegerField()

    def updateSchedule(self):
        pass

    def viewAppointments(self):
        pass

    def prescribeMedication(self):
        pass

    def __str__(self):
        return f"{self.user.username} - {self.specialization}"

class TimeBlock(models.Model):
    class DayOfWeek(models.IntegerChoices):
        MONDAY = 1, 'Monday'
        TUESDAY = 2, 'Tuesday'
        WEDNESDAY = 3, 'Wednesday'
        THURSDAY = 4, 'Thursday'
        FRIDAY = 5, 'Friday'
        SATURDAY = 6, 'Saturday'
        SUNDAY = 7, 'Sunday'
    doctor = models.ForeignKey(DoctorProfile, on_delete=models.CASCADE)
    day = models.IntegerField(choices=DayOfWeek.choices)
    start_time = models.TimeField()
    end_time = models.TimeField()

    def __str__(self):
        return f"{self.doctor.user.username} : {self.start_time} - {self.end_time}"