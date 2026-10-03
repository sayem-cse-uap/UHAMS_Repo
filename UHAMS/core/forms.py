import re

from django import forms
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from .models import User
from .security import password_matches


class LoginForm(forms.Form):
    username = forms.CharField(max_length=255)
    password = forms.CharField(widget=forms.PasswordInput)


class AccountForm(forms.ModelForm):
    """Personal details every user (any role) can edit."""

    class Meta:
        model = User
        fields = ["first_name", "last_name", "email", "phone"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"].required = True
        self.fields["phone"].required = False

    def clean_phone(self):
        phone = self.cleaned_data.get("phone", "").strip()
        if phone and not re.fullmatch(r"\+?[0-9][0-9\s\-()]{5,19}", phone):
            raise ValidationError("Enter a valid phone number (digits, spaces, - and () only).")
        return phone


class ChangePasswordForm(forms.Form):
    current_password = forms.CharField(widget=forms.PasswordInput)
    new_password = forms.CharField(widget=forms.PasswordInput)
    confirm_password = forms.CharField(widget=forms.PasswordInput)

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean_current_password(self):
        value = self.cleaned_data["current_password"]
        if not password_matches(self.user, value):
            raise ValidationError("Your current password is incorrect.")
        return value

    def clean(self):
        cleaned = super().clean()
        new = cleaned.get("new_password")
        if new:
            if new != cleaned.get("confirm_password"):
                self.add_error("confirm_password", "Passwords do not match.")
            elif new == cleaned.get("current_password"):
                self.add_error("new_password", "The new password must be different from the current one.")
            else:
                try:
                    validate_password(new, self.user)
                except ValidationError as exc:
                    self.add_error("new_password", exc)
        return cleaned

    def save(self):
        self.user.set_password(self.cleaned_data["new_password"])
        self.user.save(update_fields=["password"])
        return self.user
