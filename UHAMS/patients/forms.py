"""patients.forms - registering a patient and editing the patient's own profile."""
from django import forms
from django.db import transaction

from core.models import User
from .models import PatientProfile


class PatientRegistrationForm(forms.Form):
    """Sign-up form for a new patient. It is a plain Form (not a ModelForm)
    because it must create TWO rows - the User and the PatientProfile - so
    save() below does that by hand."""
    # --- login account fields (go to core.User) ---
    username = forms.CharField(max_length=255)
    email = forms.EmailField()
    first_name = forms.CharField(max_length=255)
    last_name = forms.CharField(max_length=255)
    password = forms.CharField(widget=forms.PasswordInput())
    confirm_password = forms.CharField(widget=forms.PasswordInput())


    # --- patient details (go to PatientProfile) ---
    bloodGroup = forms.CharField(max_length=100)
    emergencyContact = forms.CharField(max_length=100)

    # NOTE: a Meta class only has an effect on a ModelForm. On this plain Form
    # it is ignored (the fields above are what is actually used); it is kept
    # as documentation of which model the data ends up in.
    class Meta:
        model = PatientProfile
        fields = ['bloodGroup', 'emergencyContact']

    def clean(self):
        """Whole-form checks: the two passwords match and the username is free."""
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
            # create_user() hashes the password before storing it.
            user = User.objects.create_user(
                username=self.cleaned_data['username'],
                email=self.cleaned_data['email'],
                password=self.cleaned_data['password'],
                first_name=self.cleaned_data['first_name'],
                last_name=self.cleaned_data['last_name'],
                role=User.Role.PATIENT if hasattr(User, 'Role') else 'PATIENT'
            )

            # Create the PatientProfile linked to the new user
            # (the original comment here said "StaffProfile"; it is the patient's profile.)
            patient_profile = PatientProfile.objects.create(
                user=user,
                bloodGroup=self.cleaned_data['bloodGroup'],
                emergencyContact=self.cleaned_data['emergencyContact'],
            )
            return patient_profile


class PatientSettingsForm(forms.ModelForm):
    """The patient details a patient may edit on the Settings page
    (the assigned staff member is managed by staff, so it is not listed)."""
    class Meta:
        model = PatientProfile
        fields = ['bloodGroup', 'emergencyContact']
        labels = {'bloodGroup': 'Blood group', 'emergencyContact': 'Emergency contact'}
