from django.core.validators import MinValueValidator
from django.db import models, transaction

from drivers.models import DriverProfile


class Ambulance(models.Model):
    class VehicleType(models.TextChoices):
        BASIC = 'BASIC', 'Basic Life Support (BLS)'
        ADVANCED = 'ADVANCED', 'Advanced Life Support (ALS)'
        ICU = 'ICU', 'Mobile ICU'
        NEONATAL = 'NEONATAL', 'Neonatal'
        PATIENT_TRANSPORT = 'TRANSPORT', 'Patient Transport'

    class Status(models.TextChoices):
        AVAILABLE = 'AVAILABLE', 'Available'
        ON_TRIP = 'ON_TRIP', 'On Trip'
        MAINTENANCE = 'MAINTENANCE', 'Under Maintenance'
        OFFLINE = 'OFFLINE', 'Offline'

    # Human-friendly identifier, e.g. "AMB-001". This is the value stored in
    # DriverProfile.assigned_ambulance_ID so the two apps stay in sync.
    ambulance_id = models.CharField(max_length=50, unique=True)
    registration_number = models.CharField(max_length=50, unique=True)
    model_name = models.CharField(max_length=100, blank=True)
    vehicle_type = models.CharField(max_length=20, choices=VehicleType.choices, default=VehicleType.BASIC)
    capacity = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.AVAILABLE)
    equipment_notes = models.TextField(blank=True)
    last_service_date = models.DateField(null=True, blank=True)

    # Connection with the drivers app: one driver drives one ambulance.
    driver = models.OneToOneField(
        DriverProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ambulance',
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['ambulance_id']

    def __str__(self):
        return f"{self.ambulance_id} ({self.registration_number})"

    @property
    def active_call(self):
        """The emergency call this ambulance is currently dispatched to, if any."""
        return self.calls.filter(status='dispatched').first()

    @property
    def is_available(self):
        return self.status == self.Status.AVAILABLE and self.driver_id is not None

    def save(self, *args, **kwargs):
        """Save and keep DriverProfile.assigned_ambulance_ID in sync."""
        old_driver_id = old_ambulance_id = None
        if self.pk:
            old = Ambulance.objects.filter(pk=self.pk).values('driver_id', 'ambulance_id').first()
            if old:
                old_driver_id, old_ambulance_id = old['driver_id'], old['ambulance_id']

        with transaction.atomic():
            super().save(*args, **kwargs)

            # Previous driver was replaced/removed -> clear the stale reference.
            if old_driver_id and old_driver_id != self.driver_id:
                DriverProfile.objects.filter(
                    pk=old_driver_id, assigned_ambulance_ID=old_ambulance_id
                ).update(assigned_ambulance_ID='')

            if self.driver_id:
                DriverProfile.objects.filter(pk=self.driver_id).update(
                    assigned_ambulance_ID=self.ambulance_id
                )

    def delete(self, *args, **kwargs):
        with transaction.atomic():
            if self.driver_id:
                DriverProfile.objects.filter(
                    pk=self.driver_id, assigned_ambulance_ID=self.ambulance_id
                ).update(assigned_ambulance_ID='')
            return super().delete(*args, **kwargs)
