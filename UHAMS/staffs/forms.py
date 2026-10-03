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
    REGISTRATION_ROLES = [
        (value, label)
        for value, label in StaffProfile.ROLE_CHOICES
        if value in ("nurse", "receptionist", "other")
    ]

    username = forms.CharField(max_length=255)
    email = forms.EmailField()
    first_name = forms.CharField(max_length=255)
    last_name = forms.CharField(max_length=255)
    password = forms.CharField(widget=forms.PasswordInput())
    confirm_password = forms.CharField(widget=forms.PasswordInput())

    title = forms.CharField(max_length=255)
    role = forms.ChoiceField(choices=REGISTRATION_ROLES)
    department = forms.CharField(max_length=255)

    def __init__(self, *args, actor, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["access_level"] = forms.ChoiceField(
            choices=allowed_access_levels(actor), initial=StaffProfile.ACCESS_STAFF
        )

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
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
                validate_password(password)
            except ValidationError as exc:
                self.add_error("password", exc)
        return cleaned_data

    def save(self):
        # Atomic so the User and the profile are created together, or not at all.
        with transaction.atomic():
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
    role = forms.ChoiceField(choices=StaffProfile.ROLE_CHOICES)


class SalaryForm(forms.Form):
    salary = forms.DecimalField(min_value=0, max_digits=10, decimal_places=2)


class StaffDetailsForm(forms.Form):
    title = forms.CharField(max_length=255)
    department = forms.CharField(max_length=255)
    availability_status = forms.BooleanField(required=False, label="Available for assignments")

    def __init__(self, *args, access_choices=None, **kwargs):
        super().__init__(*args, **kwargs)
        # access_choices is None when the actor may not change the access level.
        if access_choices is not None:
            self.fields["access_level"] = forms.ChoiceField(choices=access_choices)


class AssignmentForm(forms.Form):
    assignment = forms.CharField(max_length=255, label="New assignment (e.g. Ward 3 night shift)")


class RoomForm(forms.Form):
    room = forms.CharField(max_length=20, label="Move to room")


class PatientChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return f"{obj.user.get_full_name() or obj.user.username} ({obj.user.username})"


class AssignPatientForm(forms.Form):
    patient = PatientChoiceField(
        queryset=PatientProfile.objects.filter(assigned_staff__isnull=True)
        .select_related("user")
        .order_by("user__username"),
        empty_label="-- choose an unassigned patient --",
    )


class ReleasePatientForm(forms.Form):
    patient = forms.ModelChoiceField(queryset=PatientProfile.objects.none())

    def __init__(self, *args, staff, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["patient"].queryset = PatientProfile.objects.filter(assigned_staff=staff)


# ----------------------------------------------------------------------
# Vacations
# ----------------------------------------------------------------------
class VacationRequestForm(forms.Form):
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
    vacation = forms.ModelChoiceField(queryset=VacationRecord.objects.select_related("staff__user"))
    decision = forms.ChoiceField(choices=[("approve", "Approve"), ("reject", "Reject")])


class VacationCancelForm(forms.Form):
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
    location = forms.CharField(max_length=255)
    description = forms.CharField(
        required=False, widget=forms.Textarea(attrs={"rows": 3}),
        label="What is happening? (optional)",
    )


class AmbulanceChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        driver = obj.driver.user.get_full_name() or obj.driver.user.username
        return f"{obj.ambulance_id} ({obj.get_vehicle_type_display()}, driver {driver})"


class DispatchForm(forms.Form):
    ambulance = AmbulanceChoiceField(
        queryset=Ambulance.objects.none(), required=False,
        empty_label="-- first available --",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["ambulance"].queryset = (
            StaffProfile.listAllAvailableAmbulances().select_related("driver__user")
        )
