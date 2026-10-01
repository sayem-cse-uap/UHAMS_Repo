from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError

from doctors.models import DoctorProfile, TimeBlock
from patients.models import PatientProfile


# Create your models here.
class Appointment(models.Model):
    class Status(models.TextChoices):
        PENDING_CONFIRMATION = "PENDING_CONFIRMATION", "Pending Confirmation"
        CONFIRMED = "CONFIRMED", "Confirmed"
        SCHEDULED_WAITING = "SCHEDULED_WAITING", "Scheduled Waiting"
        DONE = "DONE", "Done"

    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.PENDING_CONFIRMATION,
    )
    doctor = models.ForeignKey(DoctorProfile, on_delete=models.CASCADE)
    patient = models.ForeignKey(PatientProfile, on_delete=models.CASCADE)
    time_block = models.ForeignKey(TimeBlock, on_delete=models.CASCADE, null=True, blank=True)
    date = models.DateField(default=timezone.now)
    room_number = models.CharField(max_length=10, default="000")
    reason = models.TextField(blank=True, default="")

    def clean(self):
        super().clean()
        # Enforce that the time_block belongs to the selected doctor
        if self.time_block and self.doctor:
            if self.time_block.doctor_id != self.doctor_id:
                raise ValidationError(
                    {
                        "time_block": f"This time block belongs to {self.time_block.doctor}, not {self.doctor}."
                    }
                )

    def save(self, *args, **kwargs):
        self.full_clean()  # Guarantees validation runs on every save
        super().save(*args, **kwargs)


    def __str__(self):
        return f"Appointment - Doctor: {self.doctor.user.username}, Patient: {self.patient.user.username}, Room: {self.room_number}"

