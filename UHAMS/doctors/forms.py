"""doctors.forms - doctor registration, adding a time block, and editing own settings."""
from django import forms
from django.db import transaction

from core.models import User
from doctors.models import DoctorProfile, TimeBlock


class DoctorRegistrationForm(forms.Form):
    """Sign-up form for a doctor. Like the patient form, it is a plain Form that
    creates both the User and the DoctorProfile in save()."""
    # --- login account fields (go to core.User) ---
    username = forms.CharField(max_length=255)
    email = forms.EmailField()
    first_name = forms.CharField(max_length=255)
    last_name = forms.CharField(max_length=255)
    password = forms.CharField(widget=forms.PasswordInput())
    confirm_password = forms.CharField(widget=forms.PasswordInput())


    # --- doctor details (go to DoctorProfile) ---
    specialization = forms.CharField(max_length=255)
    licenseNumber = forms.CharField(max_length=255)
    consultationFee = forms.IntegerField()

    # NOTE: ignored on a plain Form; kept as documentation (see PatientRegistrationForm).
    class Meta:
        model = DoctorProfile
        fields = ['specialization', 'licenseNumber', 'consultationFee']

    def clean(self):
        """Whole-form checks: passwords match and the username is free."""
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
                role=User.Role.DOCTOR if hasattr(User, 'Role') else 'DOCTOR'
            )

            # Create the DoctorProfile linked to the new user
            # (the original comment here said "StaffProfile"; it is the doctor's profile.)
            doctor_profile = DoctorProfile.objects.create(
                user=user,
                specialization=self.cleaned_data['specialization'],
                licenseNumber=self.cleaned_data['licenseNumber'],
                consultationFee=self.cleaned_data['consultationFee']
            )
            return doctor_profile


class TimeBlockForm(forms.ModelForm):
    """Add one weekly time block to the doctor's schedule."""
    class Meta:
        model = TimeBlock
        # `doctor` is not a field: the view fills it in from the logged-in doctor.
        fields = ['day', 'start_time', 'end_time']
        widgets = {
            # type="time" shows the browser's time picker.
            'start_time': forms.TimeInput(attrs={'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'type': 'time'}),
        }

    def __init__(self, *args, doctor=None, **kwargs):
        super().__init__(*args, **kwargs)
        # Needed by clean() to compare against THIS doctor's existing blocks.
        self.doctor = doctor

    def clean(self):
        cleaned = super().clean()
        day, start, end = cleaned.get('day'), cleaned.get('start_time'), cleaned.get('end_time')
        if day and start and end:
            if end <= start:
                raise forms.ValidationError("End time must be after start time.")
            # Two time ranges on the same day overlap when
            #     existing.start < new.end  AND  existing.end > new.start
            # (touching ends, e.g. 09-10 and 10-11, are allowed).
            overlap = TimeBlock.objects.filter(
                doctor=self.doctor, day=day, start_time__lt=end, end_time__gt=start
            ).exists()
            if overlap:
                raise forms.ValidationError("This overlaps with an existing time block on that day.")
        return cleaned


class DoctorSettingsForm(forms.ModelForm):
    """What a doctor may change about themselves. The licence number is
    deliberately left out, so it is shown read-only on the Settings page."""
    consultationFee = forms.IntegerField(min_value=0, label="Consultation fee")

    class Meta:
        model = DoctorProfile
        fields = ['specialization', 'consultationFee']
