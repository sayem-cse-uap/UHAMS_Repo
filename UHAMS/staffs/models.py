from decimal import Decimal, InvalidOperation

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
    ACCESS_STAFF, ACCESS_MANAGER, ACCESS_ADMIN = "staff", "manager", "admin"
    ACCESS_CHOICES = [
        (ACCESS_STAFF, "Staff"),
        (ACCESS_MANAGER, "Manager"),
        (ACCESS_ADMIN, "Administrator"),
    ]
    # access_level values that are allowed to change other staff members' data
    MANAGER_LEVELS = {ACCESS_MANAGER, ACCESS_ADMIN}
    EDITABLE_DETAILS = {"title", "department", "availability_status", "access_level"}

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    role = models.CharField(max_length=50, choices=ROLE_CHOICES, default="other")
    salary = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    availability_status = models.BooleanField(default=True)
    current_assignment = models.CharField(max_length=255, blank=True)
    department = models.CharField(max_length=255)
    access_level = models.CharField(max_length=20, choices=ACCESS_CHOICES, default=ACCESS_STAFF)

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
    @property
    def is_manager(self):
        return (self.access_level or "").lower() in self.MANAGER_LEVELS

    @classmethod
    def _require_manager(cls, actor):
        """Only staff with a manager-level access_level may perform the action."""
        if not isinstance(actor, cls) or not actor.is_manager:
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
        """Assign a patient to this staff member or release them (PatientProfile.assigned_staff)."""
        if action == "assign":
            if not self.availability_status:
                raise ValidationError("This staff member is not available.")
            if self.is_on_leave():
                raise ValidationError("This staff member is on approved leave today.")
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
        if not new_salary.is_finite() or new_salary < 0:
            raise ValidationError("Salary must be a non-negative number.")
        self.salary = new_salary
        self.save(update_fields=["salary"])
        return self

    def changeDetailsOfStaff(self, changed_by, **details):
        self._require_manager(changed_by)
        invalid = set(details) - self.EDITABLE_DETAILS
        if invalid:
            raise ValidationError(f"Cannot change: {', '.join(sorted(invalid))}")
        if "access_level" in details and details["access_level"] not in dict(self.ACCESS_CHOICES):
            raise ValidationError(f"Invalid access level: {details['access_level']}")
        for field, value in details.items():
            setattr(self, field, value)
        self.save(update_fields=list(details))
        return self

    # ------------------------------------------------------------------
    # Vacations
    # ------------------------------------------------------------------
    def checkVacationHistoryOfStaff(self):
        return self.vacations.order_by("-start_date")

    def is_on_leave(self, on=None):
        """True if the staff member has an approved vacation covering the given date (default today)."""
        on = on or timezone.localdate()
        return self.vacations.filter(
            status=VacationRecord.APPROVED, start_date__lte=on, end_date__gte=on
        ).exists()

    def requestVacation(self, start_date, end_date, reason=""):
        """Create a pending vacation request for this staff member."""
        if start_date < timezone.localdate():
            raise ValidationError("A vacation cannot start in the past.")
        record = VacationRecord(staff=self, start_date=start_date, end_date=end_date, reason=reason)
        record.full_clean()  # runs VacationRecord.clean(): date order and overlap checks
        record.save()
        return record

    # ------------------------------------------------------------------
    # Listing staff
    # ------------------------------------------------------------------
    @classmethod
    def listAllStaff(cls):
        return cls.objects.select_related("user")

    # ------------------------------------------------------------------
    # Ambulances (uses the ambulances / drivers apps)
    # ------------------------------------------------------------------
    @staticmethod
    def listAllAvailableAmbulances():
        """Ambulances that are marked available AND have a driver."""
        from ambulances.models import Ambulance

        return Ambulance.objects.filter(status=Ambulance.Status.AVAILABLE, driver__isnull=False)

    @transaction.atomic
    def dispatchAmbulance(self, ambulance, call):
        """Send an ambulance (with its driver) to an emergency call."""
        from ambulances.models import Ambulance

        if call.status != AmbulanceCall.PENDING:
            raise ValidationError("Only pending calls can be dispatched.")
        # Re-read under a row lock so two staff cannot send the same ambulance.
        ambulance = Ambulance.objects.select_for_update().get(pk=ambulance.pk)
        if not ambulance.is_available:
            raise ValidationError("Ambulance is not available or has no driver assigned.")
        ambulance.status = Ambulance.Status.ON_TRIP
        ambulance.save(update_fields=["status"])

        call.ambulance = ambulance
        call.handled_by = self
        call.status = AmbulanceCall.DISPATCHED
        call.save(update_fields=["ambulance", "handled_by", "status"])
        return call

    @transaction.atomic
    def completeAmbulanceCall(self, call):
        """Close a dispatched call and free its ambulance."""
        from ambulances.models import Ambulance

        if call.status != AmbulanceCall.DISPATCHED:
            raise ValidationError("Only dispatched calls can be completed.")
        ambulance = call.ambulance
        if ambulance is not None and ambulance.status == Ambulance.Status.ON_TRIP:
            ambulance.status = Ambulance.Status.AVAILABLE
            ambulance.save(update_fields=["status"])
        call.status = AmbulanceCall.COMPLETED
        call.save(update_fields=["status"])
        return call

    @transaction.atomic
    def cancelAmbulanceCall(self, call):
        """Cancel a pending or dispatched call; a dispatched call frees its ambulance."""
        from ambulances.models import Ambulance

        if call.status not in (AmbulanceCall.PENDING, AmbulanceCall.DISPATCHED):
            raise ValidationError("Only open calls can be cancelled.")
        ambulance = call.ambulance
        if call.status == AmbulanceCall.DISPATCHED and ambulance is not None \
                and ambulance.status == Ambulance.Status.ON_TRIP:
            ambulance.status = Ambulance.Status.AVAILABLE
            ambulance.save(update_fields=["status"])
        call.status = AmbulanceCall.CANCELLED
        call.save(update_fields=["status"])
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
        ambulance = self.listAllAvailableAmbulances().select_for_update().first()
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
    PENDING, APPROVED, REJECTED = "pending", "approved", "rejected"
    STATUS_CHOICES = [
        (PENDING, "Pending"),
        (APPROVED, "Approved"),
        (REJECTED, "Rejected"),
    ]

    staff = models.ForeignKey(StaffProfile, on_delete=models.CASCADE, related_name="vacations")
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=PENDING)
    reviewed_by = models.ForeignKey(
        StaffProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-start_date"]

    @property
    def approved(self):
        return self.status == self.APPROVED

    def clean(self):
        if not (self.start_date and self.end_date):
            return
        if self.end_date < self.start_date:
            raise ValidationError("End date cannot be before start date.")
        if self.staff_id and self.status in (self.PENDING, self.APPROVED):
            overlap = VacationRecord.objects.filter(
                staff_id=self.staff_id,
                status__in=[self.PENDING, self.APPROVED],
                start_date__lte=self.end_date,
                end_date__gte=self.start_date,
            ).exclude(pk=self.pk)
            if overlap.exists():
                raise ValidationError("This overlaps with another pending or approved vacation.")

    # -- review workflow ------------------------------------------------
    def review_block_reason(self, reviewer):
        """None if `reviewer` may approve/reject this request, otherwise why not."""
        if not isinstance(reviewer, StaffProfile) or not reviewer.is_manager:
            return "Only managers can review vacation requests."
        if self.status != self.PENDING:
            return "Only pending requests can be reviewed."
        is_admin = reviewer.access_level == StaffProfile.ACCESS_ADMIN
        if reviewer.pk == self.staff_id and not is_admin:
            return "You cannot review your own vacation request."
        if self.staff.access_level == StaffProfile.ACCESS_ADMIN and not is_admin:
            return "Only an administrator can review an administrator's request."
        return None

    def _review(self, reviewer, new_status):
        reason = self.review_block_reason(reviewer)
        if reason:
            if self.status != self.PENDING:
                raise ValidationError(reason)
            raise PermissionDenied(reason)
        self.status = new_status
        self.reviewed_by = reviewer
        self.reviewed_at = timezone.now()
        self.save(update_fields=["status", "reviewed_by", "reviewed_at"])
        return self

    def approve(self, reviewer):
        return self._review(reviewer, self.APPROVED)

    def reject(self, reviewer):
        return self._review(reviewer, self.REJECTED)

    def cancel(self, staff):
        """The owner withdraws a request that has not been reviewed yet."""
        if staff.pk != self.staff_id:
            raise PermissionDenied("You can only cancel your own vacation requests.")
        if self.status != self.PENDING:
            raise ValidationError("Only pending requests can be cancelled.")
        self.delete()

    def __str__(self):
        return f"{self.staff} on leave {self.start_date} to {self.end_date}"


class AmbulanceCall(models.Model):
    PENDING, DISPATCHED, COMPLETED, CANCELLED = "pending", "dispatched", "completed", "cancelled"
    STATUS_CHOICES = [
        (PENDING, "Pending"),
        (DISPATCHED, "Dispatched"),
        (COMPLETED, "Completed"),
        (CANCELLED, "Cancelled"),
    ]

    location = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=PENDING)
    # Points at the real ambulance fleet in the `ambulances` app.
    ambulance = models.ForeignKey(
        "ambulances.Ambulance", on_delete=models.SET_NULL, null=True, blank=True, related_name="calls"
    )
    handled_by = models.ForeignKey(
        StaffProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name="handled_calls"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Call at {self.location} [{self.get_status_display()}]"
