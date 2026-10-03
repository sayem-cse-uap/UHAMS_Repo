"""
ambulances.models - the ambulance fleet.

How the ambulance pieces fit together:

    drivers.DriverProfile  <--1:1--  Ambulance  <--many--  staffs.AmbulanceCall
       (who drives it)               (the vehicle)         (emergency calls it was sent to)

An ambulance is "available for dispatch" only when its status is AVAILABLE *and*
it has a driver (see `is_available`). Dispatching sets it to ON_TRIP; completing
or cancelling the call sets it back to AVAILABLE (staffs/models.py).
"""
from django.core.validators import MinValueValidator
from django.db import models, transaction

from drivers.models import DriverProfile


class Ambulance(models.Model):
    class VehicleType(models.TextChoices):
        # (stored value, label shown on screen)
        BASIC = 'BASIC', 'Basic Life Support (BLS)'
        ADVANCED = 'ADVANCED', 'Advanced Life Support (ALS)'
        ICU = 'ICU', 'Mobile ICU'
        NEONATAL = 'NEONATAL', 'Neonatal'
        PATIENT_TRANSPORT = 'TRANSPORT', 'Patient Transport'

    class Status(models.TextChoices):
        AVAILABLE = 'AVAILABLE', 'Available'          # free and can be dispatched
        ON_TRIP = 'ON_TRIP', 'On Trip'                # currently answering a call
        MAINTENANCE = 'MAINTENANCE', 'Under Maintenance'
        OFFLINE = 'OFFLINE', 'Offline'

    # Human-friendly identifier, e.g. "AMB-001". This is the value stored in
    # DriverProfile.assigned_ambulance_ID so the two apps stay in sync.
    ambulance_id = models.CharField(max_length=50, unique=True)
    registration_number = models.CharField(max_length=50, unique=True)   # number plate
    model_name = models.CharField(max_length=100, blank=True)
    vehicle_type = models.CharField(max_length=20, choices=VehicleType.choices, default=VehicleType.BASIC)
    # Number of patients it can carry; at least 1.
    capacity = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.AVAILABLE)
    equipment_notes = models.TextField(blank=True)
    last_service_date = models.DateField(null=True, blank=True)

    # Connection with the drivers app: one driver drives one ambulance.
    # OneToOne => a driver can be linked to at most one ambulance (and vice versa).
    # SET_NULL => deleting the driver profile just leaves the ambulance without a driver.
    # related_name='ambulance' lets you write driver_profile.ambulance.
    driver = models.OneToOneField(
        DriverProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ambulance',
    )

    created_at = models.DateTimeField(auto_now_add=True)   # set when first saved
    updated_at = models.DateTimeField(auto_now=True)       # refreshed on every save

    class Meta:
        ordering = ['ambulance_id']

    def __str__(self):
        return f"{self.ambulance_id} ({self.registration_number})"

    @property
    def active_call(self):
        """The emergency call this ambulance is currently dispatched to, if any."""
        # `calls` is the reverse side of AmbulanceCall.ambulance. The status is
        # compared with the plain string 'dispatched' (AmbulanceCall.DISPATCHED)
        # because importing staffs.models here would be a circular import.
        return self.calls.filter(status='dispatched').first()

    @property
    def is_available(self):
        """Can be sent to a call: marked available AND someone is assigned to drive it."""
        return self.status == self.Status.AVAILABLE and self.driver_id is not None

    def save(self, *args, **kwargs):
        """Save and keep DriverProfile.assigned_ambulance_ID in sync."""
        # Step 1: if this ambulance already exists, remember who its driver and
        # ambulance_id were BEFORE this save, so stale references can be cleaned up.
        old_driver_id = old_ambulance_id = None
        if self.pk:
            old = Ambulance.objects.filter(pk=self.pk).values('driver_id', 'ambulance_id').first()
            if old:
                old_driver_id, old_ambulance_id = old['driver_id'], old['ambulance_id']

        # Step 2: do the save and the driver updates together in one transaction.
        with transaction.atomic():
            super().save(*args, **kwargs)

            # Previous driver was replaced/removed -> clear the stale reference.
            # (The extra assigned_ambulance_ID=old_ambulance_id condition makes sure we
            # only clear it if it still points at THIS ambulance.)
            if old_driver_id and old_driver_id != self.driver_id:
                DriverProfile.objects.filter(
                    pk=old_driver_id, assigned_ambulance_ID=old_ambulance_id
                ).update(assigned_ambulance_ID='')

            # Current driver (if any) gets this ambulance's ID written to their profile.
            # .update() runs a direct SQL UPDATE; it skips model save() hooks on purpose.
            if self.driver_id:
                DriverProfile.objects.filter(pk=self.driver_id).update(
                    assigned_ambulance_ID=self.ambulance_id
                )

    def delete(self, *args, **kwargs):
        """Delete the ambulance and clear its driver's text reference."""
        with transaction.atomic():
            if self.driver_id:
                DriverProfile.objects.filter(
                    pk=self.driver_id, assigned_ambulance_ID=self.ambulance_id
                ).update(assigned_ambulance_ID='')
            return super().delete(*args, **kwargs)
