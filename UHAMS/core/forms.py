"""
core.forms - forms shared by every role: logging in, editing your own account
details, and changing your password.

A Django Form does three jobs: it renders the HTML inputs ({{ form.as_p }} in
the template), it validates what the user submitted (is_valid()), and it hands
back clean Python values (form.cleaned_data).
"""
import re

from django import forms
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from .models import User
from .security import password_matches


class LoginForm(forms.Form):
    """Just two fields; the actual credential check happens in views.loginView
    (so that one generic error message can be shown for any failure)."""
    username = forms.CharField(max_length=255)
    # PasswordInput renders <input type="password"> so the text is masked.
    password = forms.CharField(widget=forms.PasswordInput)


class AccountForm(forms.ModelForm):
    """Personal details every user (any role) can edit."""

    class Meta:
        model = User
        # Deliberately NOT included: username, role, password, is_staff, ...
        # A user must never be able to change their own role or permissions.
        fields = ["first_name", "last_name", "email", "phone"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Override the defaults taken from the model: email is mandatory on
        # this form, phone is optional.
        self.fields["email"].required = True
        self.fields["phone"].required = False

    def clean_phone(self):
        """Field-level validation: runs automatically for the `phone` field."""
        phone = self.cleaned_data.get("phone", "").strip()
        # Optional "+", then a digit, then 5-19 more digits/spaces/dashes/brackets.
        # (So 6-20 characters in total, matching max_length=20 on the model.)
        if phone and not re.fullmatch(r"\+?[0-9][0-9\s\-()]{5,19}", phone):
            raise ValidationError("Enter a valid phone number (digits, spaces, - and () only).")
        return phone


class ChangePasswordForm(forms.Form):
    """Change-password form. Requires the CURRENT password first, so that
    someone who walks up to an unlocked, logged-in computer cannot silently
    take over the account."""
    current_password = forms.CharField(widget=forms.PasswordInput)
    new_password = forms.CharField(widget=forms.PasswordInput)
    confirm_password = forms.CharField(widget=forms.PasswordInput)

    def __init__(self, user, *args, **kwargs):
        # The form needs to know WHICH user is changing their password, so the
        # view passes it as the first argument.
        super().__init__(*args, **kwargs)
        self.user = user

    def clean_current_password(self):
        """Verify the current password against the stored hash."""
        value = self.cleaned_data["current_password"]
        if not password_matches(self.user, value):
            raise ValidationError("Your current password is incorrect.")
        return value

    def clean(self):
        """Form-level validation: looks at several fields together."""
        cleaned = super().clean()
        new = cleaned.get("new_password")
        if new:
            if new != cleaned.get("confirm_password"):
                self.add_error("confirm_password", "Passwords do not match.")
            elif new == cleaned.get("current_password"):
                self.add_error("new_password", "The new password must be different from the current one.")
            else:
                try:
                    # Run the AUTH_PASSWORD_VALIDATORS from settings.py
                    # (length, not too common, not all digits, not like the username...).
                    validate_password(new, self.user)
                except ValidationError as exc:
                    self.add_error("new_password", exc)
        return cleaned

    def save(self):
        # set_password() hashes the new password before storing it.
        self.user.set_password(self.cleaned_data["new_password"])
        # update_fields keeps the UPDATE statement to the one column we changed.
        self.user.save(update_fields=["password"])
        return self.user
