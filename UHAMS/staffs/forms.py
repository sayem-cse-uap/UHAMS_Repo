from django import forms
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction

from core.models import User
from staffs.models import StaffProfile


class StaffRegistrationForm(forms.Form):
    # Doctors and drivers register on their own pages, and "admin" is not
    # self-service, so only these roles are offered here.
    SELF_SERVICE_ROLES = [
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
    role = forms.ChoiceField(choices=SELF_SERVICE_ROLES)
    department = forms.CharField(max_length=255)

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

    def save(self, commit=True):
        # Atomic so the User and the profile are created together, or not at all.
        # New staff always start at the lowest access level; a manager/admin
        # promotes them later (access level is never chosen at sign-up).
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
                access_level=StaffProfile.ACCESS_STAFF,
            )


class StaffSettingsForm(forms.ModelForm):
    """What a staff member may change about themselves (title, role, salary and
    access level are managed by a manager, see StaffProfile.change* methods)."""

    class Meta:
        model = StaffProfile
        fields = ["availability_status"]
        labels = {"availability_status": "I am available for assignments"}
