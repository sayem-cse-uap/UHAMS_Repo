from decimal import Decimal, InvalidOperation

from django.apps import apps
from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import models, transaction
from django.utils import timezone


class StaffProfile(models.Model):
    ROLE_CHOICES = [
        ("doctor", "Doctor"),
        ("nurse", "Nurse"),
        ("receptionist", "Receptionist"),
        ("driver", "Driver"),
        ("admin", "Administrator"),
        ("other", "Other"),
    ]
    # access_level values that are allowed to change other staff members' data
    MANAGER_LEVELS = {"admin", "manager"}
    EDITABLE_DETAILS = {"title", "department", "availability_status", "access_level"}

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    role = models.CharField(max_length=50, choices=ROLE_CHOICES, default="other")
    salary = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    availability_status = models.BooleanField(default=True)
    current_assignment = models.CharField(max_length=255, blank=True)
    department = models.CharField(max_length=255)
    access_level = models.CharField(max_length=255)

    class Meta:
        ordering = ["user__username"]
        verbose_name = "Staff profile"
        verbose_name_plural = "Staff profiles"

    def __str__(self):
        name = self.user.get_full_name() or self.user.get_username()
        return f"{name} ({self.get_role_display()}) - {self.department}"

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @classmethod
    def _require_manager(cls, actor):
        """Only staff with a manager-level access_level may perform the action."""
        if actor is None or actor.access_level.lower() not in cls.MANAGER_LEVELS:
            raise PermissionDenied("You do not have permission to perform this action.")

    # ------------------------------------------------------------------
    # Assignments & rooms
    # ------------------------------------------------------------------
    @transaction.atomic
    def assignStaff(self, assignment, assigned_by=None):
        """Close the current assignment (if any) and start a new one."""
        now = timezone.now()
        self.assignments.filter(ended_at__isnull=True).update(ended_at=now)
        record = StaffAssignment.objects.create(
            staff=self, assignment=assignment, started_at=now, assigned_by=assigned_by
        )
        self.current_assignment = assignment
        self.save(update_fields=["current_assignment"])
        return record

    def ReAllocateRoom(self, room, assigned_by=None):
        """Move this staff member to another room (logged in assignment history)."""
        return self.assignStaff(f"Room {room}", assigned_by=assigned_by)

    def checkStaffAssignmentHistory(self):
        return self.assignments.order_by("-started_at")

    # ------------------------------------------------------------------
    # Patients
    # ------------------------------------------------------------------
    @transaction.atomic
    def managePatient(self, patient, action="assign"):
        """
        Assign a patient to this staff member or release them.
        Assumes the Patient model has a nullable `assigned_staff` FK to StaffProfile.
        """
        if action == "assign":
            if not self.availability_status:
                raise ValidationError("This staff member is not available.")
            patient.assigned_staff = self
        elif action == "release":
            if patient.assigned_staff_id != self.pk:
                raise ValidationError("Patient is not assigned to this staff member.")
            patient.assigned_staff = None
        else:
            raise ValueError("action must be 'assign' or 'release'.")
        patient.save(update_fields=["assigned_staff"])
        return patient

    # ------------------------------------------------------------------
    # Role, salary, details
    # ------------------------------------------------------------------
    def checkRoleOfStaff(self):
        return self.get_role_display()

    def changeRoleOfStaff(self, new_role, changed_by):
        self._require_manager(changed_by)
        if new_role not in dict(self.ROLE_CHOICES):
            raise ValidationError(f"Invalid role: {new_role}")
        self.role = new_role
        self.save(update_fields=["role"])
        return self

    def changeSalaryOfStaff(self, new_salary, changed_by):
        self._require_manager(changed_by)
        try:
            new_salary = Decimal(str(new_salary))
        except InvalidOperation:
            raise ValidationError("Salary must be a valid number.")
        if new_salary < 0:
            raise ValidationError("Salary cannot be negative.")
        self.salary = new_salary
        self.save(update_fields=["salary"])
        return self

    def changeDetailsOfStaff(self, changed_by, **details):
        self._require_manager(changed_by)
        invalid = set(details) - self.EDITABLE_DETAILS
        if invalid:
            raise ValidationError(f"Cannot change: {', '.join(sorted(invalid))}")
        for field, value in details.items():
            setattr(self, field, value)
        self.save(update_fields=list(details))
        return self

    # ------------------------------------------------------------------
    # Vacations
    # ------------------------------------------------------------------
    def checkVacationHistoryOfStaff(self):
        return self.vacations.order_by("-start_date")

    # ------------------------------------------------------------------
    # Listing staff
    # ------------------------------------------------------------------
    @classmethod
    def listAllStaff(cls):
        return cls.objects.select_related("user")

    @classmethod
    def listAllAvailableStaff(cls):
        return cls.listAllStaff().filter(availability_status=True)

    # ------------------------------------------------------------------
    # Ambulances
    # ------------------------------------------------------------------
    @staticmethod
    def listAllAvailableAmbulances():
        return Ambulance.objects.filter(status=Ambulance.AVAILABLE)

    @classmethod
    def listAllAvailableDrivers(cls):
        return cls.listAllAvailableStaff().filter(role="driver")

    @transaction.atomic
    def assignDriverToAmbulance(self, ambulance):
        """Assign this staff member (must be an available driver) to an ambulance."""
        if self.role != "driver":
            raise ValidationError("Only staff with the driver role can be assigned.")
        if not self.availability_status:
            raise ValidationError("This driver is not available.")
        ambulance.driver = self
        ambulance.save(update_fields=["driver"])
        return ambulance

    @transaction.atomic
    def dispatchAmbulance(self, ambulance, call):
        """Send an ambulance (with its driver) to an emergency call."""
        if ambulance.status != Ambulance.AVAILABLE:
            raise ValidationError("Ambulance is not available.")
        if ambulance.driver is None:
            raise ValidationError("Ambulance has no driver assigned.")
        ambulance.status = Ambulance.ON_CALL
        ambulance.save(update_fields=["status"])

        driver = ambulance.driver
        driver.availability_status = False
        driver.save(update_fields=["availability_status"])

        call.ambulance = ambulance
        call.handled_by = self
        call.status = AmbulanceCall.DISPATCHED
        call.save(update_fields=["ambulance", "handled_by", "status"])
        return call

    @transaction.atomic
    def emergencyAmbulanceCallRequestHandling(self, location, description=""):
        """
        Log an emergency call and dispatch the first ambulance that is available
        and has a driver. If none is free, the call stays 'pending'.
        """
        call = AmbulanceCall.objects.create(
            location=location, description=description, handled_by=self
        )
        ambulance = (
            self.listAllAvailableAmbulances()
            .filter(driver__isnull=False, driver__availability_status=True)
            .select_for_update()
            .first()
        )
        if ambulance is None:
            return call
        return self.dispatchAmbulance(ambulance, call)


class StaffAssignment(models.Model):
    staff = models.ForeignKey(StaffProfile, on_delete=models.CASCADE, related_name="assignments")
    assignment = models.CharField(max_length=255)
    started_at = models.DateTimeField(default=timezone.now)
    ended_at = models.DateTimeField(null=True, blank=True)
    assigned_by = models.ForeignKey(
        StaffProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )

    class Meta:
        ordering = ["-started_at"]

    def __str__(self):
        return f"{self.staff} -> {self.assignment} (from {self.started_at:%Y-%m-%d})"


class VacationRecord(models.Model):
    staff = models.ForeignKey(StaffProfile, on_delete=models.CASCADE, related_name="vacations")
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.CharField(max_length=255, blank=True)
    approved = models.BooleanField(default=False)

    class Meta:
        ordering = ["-start_date"]

    def clean(self):
        if self.end_date < self.start_date:
            raise ValidationError("End date cannot be before start date.")

    def __str__(self):
        return f"{self.staff} on leave {self.start_date} to {self.end_date}"


class Ambulance(models.Model):
    AVAILABLE, ON_CALL, MAINTENANCE = "available", "on_call", "maintenance"
    STATUS_CHOICES = [
        (AVAILABLE, "Available"),
        (ON_CALL, "On call"),
        (MAINTENANCE, "Under maintenance"),
    ]

    plate_number = models.CharField(max_length=20, unique=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=AVAILABLE)
    driver = models.ForeignKey(
        StaffProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name="ambulances"
    )

    def __str__(self):
        return f"Ambulance {self.plate_number} ({self.get_status_display()})"


class AmbulanceCall(models.Model):
    PENDING, DISPATCHED, COMPLETED = "pending", "dispatched", "completed"
    STATUS_CHOICES = [
        (PENDING, "Pending"),
        (DISPATCHED, "Dispatched"),
        (COMPLETED, "Completed"),
    ]

    location = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=PENDING)
    ambulance = models.ForeignKey(Ambulance, on_delete=models.SET_NULL, null=True, blank=True)
    handled_by = models.ForeignKey(
        StaffProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name="handled_calls"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Call at {self.location} [{self.get_status_display()}]"