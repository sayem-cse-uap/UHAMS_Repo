"""
appointments.models - the Appointment that connects a patient to a doctor.

This app has no views or urls of its own: the patient's side lives in
patients/views.py (request an appointment) and the doctor's side in
doctors/views.py (confirm it). This app only owns the data model and the two
forms those views use (appointments/forms.py).
"""
from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError

from doctors.models import DoctorProfile, TimeBlock
from patients.models import PatientProfile


# Create your models here.
class Appointment(models.Model):
    class Status(models.TextChoices):
        # Life cycle: PENDING_CONFIRMATION (patient asked) -> CONFIRMED (doctor
        # assigned a time block and date). SCHEDULED_WAITING and DONE are
        # further states that the screens already know how to display.
        PENDING_CONFIRMATION = "PENDING_CONFIRMATION", "Pending Confirmation"
        CONFIRMED = "CONFIRMED", "Confirmed"
        SCHEDULED_WAITING = "SCHEDULED_WAITING", "Scheduled Waiting"
        DONE = "DONE", "Done"

    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.PENDING_CONFIRMATION,
    )
    # Deleting a doctor or patient also deletes their appointments (CASCADE).
    doctor = models.ForeignKey(DoctorProfile, on_delete=models.CASCADE)
    patient = models.ForeignKey(PatientProfile, on_delete=models.CASCADE)
    # Empty until the doctor confirms the request and picks one of their weekly blocks.
    time_block = models.ForeignKey(TimeBlock, on_delete=models.CASCADE, null=True, blank=True)
    # While pending this is the patient's PREFERRED date; once confirmed it is the real one.
    date = models.DateField(default=timezone.now)
    # "000" is the placeholder meaning "no room assigned yet".
    room_number = models.CharField(max_length=10, default="000")
    reason = models.TextField(blank=True, default="")

    def clean(self):
        """Model-level validation (run by full_clean())."""
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
        # Django does not call clean() on a normal save(); calling full_clean()
        # here means the rule above is enforced no matter where an Appointment
        # is saved from (views, admin, shell, ...).
        self.full_clean()  # Guarantees validation runs on every save
        super().save(*args, **kwargs)


    def __str__(self):
        return f"Appointment - Doctor: {self.doctor.user.username}, Patient: {self.patient.user.username}, Room: {self.room_number}"
