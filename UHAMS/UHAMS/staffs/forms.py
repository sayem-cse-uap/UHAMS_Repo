from django import forms
from django.db import transaction

from core.models import User
from staffs.models import StaffProfile


class StaffRegistrationForm(forms.Form):
    username = forms.CharField(max_length=255)
    email = forms.EmailField()
    first_name = forms.CharField(max_length=255)
    last_name = forms.CharField(max_length=255)
    password = forms.CharField(widget=forms.PasswordInput())
    confirm_password = forms.CharField(widget=forms.PasswordInput())


    title = forms.CharField(max_length=255)
    department = forms.CharField(max_length=255)
    access_level = forms.CharField(max_length=255)

    class Meta:
        model = StaffProfile
        fields = ['title', 'department', 'access_level']

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
                role=User.Role.STAFF if hasattr(User, 'Role') else 'STAFF'
            )

            # Create StaffProfile linked to the new user
            staff_profile = StaffProfile.objects.create(
                user=user,
                title=self.cleaned_data['title'],
                department=self.cleaned_data['department'],
                access_level=self.cleaned_data['access_level']
            )
            return staff_profile
