from django import forms
from django.db import transaction

from core.models import User
from drivers.models import DriverProfile


class DriverRegistrationForm(forms.Form):
    username = forms.CharField(max_length=255)
    email = forms.EmailField()
    first_name = forms.CharField(max_length=255)
    last_name = forms.CharField(max_length=255)
    password = forms.CharField(widget=forms.PasswordInput())
    confirm_password = forms.CharField(widget=forms.PasswordInput())


    driver_license_number = forms.CharField(max_length=255)
    shift_status = forms.CharField(max_length=255)
    assigned_ambulance_ID = forms.CharField(max_length=255)

    class Meta:
        model = DriverProfile
        fields = ['driver_license_number', 'shift_status', 'assigned_ambulance_ID']

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password != confirm_password:
            raise forms.ValidationError("Passwords do not match.")

        if User.objects.filter(username=cleaned_data.get("username")).exists():
            raise forms.ValidationError("Username is already taken.")

        return cleaned_data

    def save(self, commit=True):
        # Use an atomic transaction so both User and Profile are created, or neither is
        with transaction.atomic():
            user = User.objects.create_user(
                username=self.cleaned_data['username'],
                email=self.cleaned_data['email'],
                password=self.cleaned_data['password'],
                first_name=self.cleaned_data['first_name'],
                last_name=self.cleaned_data['last_name'],
                role=User.Role.DRIVER if hasattr(User, 'Role') else 'DRIVER'
            )

            # Create StaffProfile linked to the new user
            driver_profile = DriverProfile.objects.create(
                user=user,
                driver_license_number=self.cleaned_data['driver_license_number'],
                shift_status=self.cleaned_data['shift_status'],
                assigned_ambulance_ID=self.cleaned_data['assigned_ambulance_ID']
            )
            return driver_profile
