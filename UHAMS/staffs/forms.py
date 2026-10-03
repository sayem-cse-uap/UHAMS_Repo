"""
staffs.forms - every form used on the staff screens.

Most of these are small single-purpose forms. The manager's "edit staff member"
page (staffs/views.py -> manage_staff_detail) shows many of them at once, one
per action (change role, change salary, assign a patient, ...), and the form that
was actually submitted is chosen by a hidden "action" field.
"""
from django import forms
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction

from core.models import User
from ambulances.models import Ambulance
from patients.models import PatientProfile
from staffs.models import StaffProfile, VacationRecord
from staffs.permissions import allowed_access_levels


class StaffRegistrationForm(forms.Form):
    """Used by managers to create staff accounts. Doctors and drivers register on
    their own pages, and the 'admin' job role is assigned later via the edit screen."""
    # Only these job roles can be picked at registration time (built from
    # ROLE_CHOICES so the labels stay consistent with the rest of the project).
    REGISTRATION_ROLES = [
        (value, label)
        for value, label in StaffProfile.ROLE_CHOICES
        if value in ("nurse", "receptionist", "other")
    ]

    # --- login account (stored on core.User) ---
    username = forms.CharField(max_length=255)
    email = forms.EmailField()
    first_name = forms.CharField(max_length=255)
    last_name = forms.CharField(max_length=255)
    password = forms.CharField(widget=forms.PasswordInput())
    confirm_password = forms.CharField(widget=forms.PasswordInput())

    # --- staff details (stored on StaffProfile) ---
    title = forms.CharField(max_length=255)
    role = forms.ChoiceField(choices=REGISTRATION_ROLES)
    department = forms.CharField(max_length=255)

    def __init__(self, *args, actor, **kwargs):
        # `actor` (keyword-only) is the manager filling in the form.
        super().__init__(*args, **kwargs)
        # The access-level dropdown is built per request: a plain manager is not
        # offered "Administrator", an administrator is.
        self.fields["access_level"] = forms.ChoiceField(
            choices=allowed_access_levels(actor), initial=StaffProfile.ACCESS_STAFF
        )

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        # iexact = case-insensitive, so "Bob" and "bob" count as the same name.
        if User.objects.filter(username__iexact=username).exists():
            raise ValidationError("Username is already taken.")
        return username

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password and confirm_password and password != confirm_password:
            self.add_error("confirm_password", "Passwords do not match.")
        elif password:
            try:
                # Apply the password rules from settings.AUTH_PASSWORD_VALIDATORS.
                validate_password(password)
            except ValidationError as exc:
                self.add_error("password", exc)
        return cleaned_data

    def save(self):
        # Atomic so the User and the profile are created together, or not at all.
        with transaction.atomic():
            # create_user() hashes the password for us.
            user = User.objects.create_user(
                username=self.cleaned_data["username"],
                email=self.cleaned_data["email"],
                password=self.cleaned_data["password"],
                first_name=self.cleaned_data["first_name"],
                last_name=self.cleaned_data["last_name"],
                role=User.Role.STAFF,
            )
            return StaffProfile.objects.create(
                user=user,
                title=self.cleaned_data["title"],
                role=self.cleaned_data["role"],
                department=self.cleaned_data["department"],
                access_level=self.cleaned_data["access_level"],
            )


class StaffSettingsForm(forms.ModelForm):
    """What a staff member may change about themselves (title, role, salary and
    access level are managed by a manager on the Manage Staff screens)."""

    class Meta:
        model = StaffProfile
        fields = ["availability_status"]
        labels = {"availability_status": "I am available for assignments"}


# ----------------------------------------------------------------------
# Manager screens
# ----------------------------------------------------------------------
class RoleForm(forms.Form):
    """Change a staff member's job role."""
    role = forms.ChoiceField(choices=StaffProfile.ROLE_CHOICES)


class SalaryForm(forms.Form):
    """Change a staff member's salary (non-negative, max 10 digits, 2 decimals)."""
    salary = forms.DecimalField(min_value=0, max_digits=10, decimal_places=2)


class StaffDetailsForm(forms.Form):
    """Edit title / department / availability, and (if allowed) the access level."""
    title = forms.CharField(max_length=255)
    department = forms.CharField(max_length=255)
    # required=False: an unticked checkbox sends nothing, which must mean "False", not "missing".
    availability_status = forms.BooleanField(required=False, label="Available for assignments")

    def __init__(self, *args, access_choices=None, **kwargs):
        super().__init__(*args, **kwargs)
        # access_choices is None when the actor may not change the access level.
        # In that case the field simply does not exist, so it also cannot be
        # forged by posting an extra value.
        if access_choices is not None:
            self.fields["access_level"] = forms.ChoiceField(choices=access_choices)


class AssignmentForm(forms.Form):
    """Give the staff member a new assignment (free text)."""
    assignment = forms.CharField(max_length=255, label="New assignment (e.g. Ward 3 night shift)")


class RoomForm(forms.Form):
    """Move the staff member to a different room."""
    room = forms.CharField(max_length=20, label="Move to room")


class PatientChoiceField(forms.ModelChoiceField):
    """Dropdown of patients that shows 'Full Name (username)' instead of the model's __str__."""
    def label_from_instance(self, obj):
        return f"{obj.user.get_full_name() or obj.user.username} ({obj.user.username})"


class AssignPatientForm(forms.Form):
    """Pick an UNASSIGNED patient to give to this staff member."""
    patient = PatientChoiceField(
        # Only patients without a staff member yet; select_related loads their user in the same query.
        queryset=PatientProfile.objects.filter(assigned_staff__isnull=True)
        .select_related("user")
        .order_by("user__username"),
        empty_label="-- choose an unassigned patient --",
    )


class ReleasePatientForm(forms.Form):
    """Release one of THIS staff member's patients. The allowed choices are
    limited to patients assigned to `staff`, so you cannot release somebody else's patient."""
    patient = forms.ModelChoiceField(queryset=PatientProfile.objects.none())

    def __init__(self, *args, staff, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["patient"].queryset = PatientProfile.objects.filter(assigned_staff=staff)


# ----------------------------------------------------------------------
# Vacations
# ----------------------------------------------------------------------
class VacationRequestForm(forms.Form):
    """A staff member asks for time off. (The 'not in the past' and 'no overlap'
    rules are enforced in the model: StaffProfile.requestVacation.)"""
    # type="date" makes the browser show a date picker.
    start_date = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))
    end_date = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))
    reason = forms.CharField(max_length=255, required=False)

    def clean(self):
        cleaned = super().clean()
        start, end = cleaned.get("start_date"), cleaned.get("end_date")
        if start and end and end < start:
            self.add_error("end_date", "End date cannot be before the start date.")
        return cleaned


class VacationReviewForm(forms.Form):
    """A manager's decision on one request: which one, and approve or reject."""
    # ModelChoiceField turns the posted id into a VacationRecord object (or an error if it does not exist).
    vacation = forms.ModelChoiceField(queryset=VacationRecord.objects.select_related("staff__user"))
    decision = forms.ChoiceField(choices=[("approve", "Approve"), ("reject", "Reject")])


class VacationCancelForm(forms.Form):
    """Withdraw a request. Only the staff member's own PENDING requests are valid choices."""
    vacation = forms.ModelChoiceField(queryset=VacationRecord.objects.none())

    def __init__(self, *args, staff, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["vacation"].queryset = VacationRecord.objects.filter(
            staff=staff, status=VacationRecord.PENDING
        )


# ----------------------------------------------------------------------
# Emergency ambulance calls
# ----------------------------------------------------------------------
class EmergencyCallForm(forms.Form):
    """Log a new emergency call."""
    location = forms.CharField(max_length=255)
    description = forms.CharField(
        required=False, widget=forms.Textarea(attrs={"rows": 3}),
        label="What is happening? (optional)",
    )


class AmbulanceChoiceField(forms.ModelChoiceField):
    """Dropdown label such as 'AMB-001 (Mobile ICU, driver Jane Doe)'."""
    def label_from_instance(self, obj):
        driver = obj.driver.user.get_full_name() or obj.driver.user.username
        return f"{obj.ambulance_id} ({obj.get_vehicle_type_display()}, driver {driver})"


class DispatchForm(forms.Form):
    """Choose which ambulance to send to a pending call (or leave empty = first available)."""
    ambulance = AmbulanceChoiceField(
        queryset=Ambulance.objects.none(), required=False,
        empty_label="-- first available --",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # The queryset is set here (not at class level) so it is evaluated fresh
        # on every request instead of once at import time.
        self.fields["ambulance"].queryset = (
            StaffProfile.listAllAvailableAmbulances().select_related("driver__user")
        )
