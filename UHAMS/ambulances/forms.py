"""ambulances.forms - the staff form for creating/editing an ambulance, and the
small "change status" form used by staff and by the assigned driver."""
import datetime

from django import forms
from django.db.models import Q

from drivers.models import DriverProfile
from .models import Ambulance


class DriverChoiceField(forms.ModelChoiceField):
    """Dropdown label such as 'Jane Doe (License: ABC123)'."""
    def label_from_instance(self, obj):
        name = obj.user.get_full_name() or obj.user.username
        return f"{name} (License: {obj.driver_license_number})"


class AmbulanceForm(forms.ModelForm):
    # Declared explicitly so we can customise the dropdown (label text, optional,
    # "-- Unassigned --" as the empty choice). Its queryset is filled in __init__.
    driver = DriverChoiceField(queryset=DriverProfile.objects.none(), required=False, empty_label="-- Unassigned --")

    class Meta:
        model = Ambulance
        fields = [
            'ambulance_id', 'registration_number', 'model_name', 'vehicle_type',
            'capacity', 'status', 'last_service_date', 'driver', 'equipment_notes',
        ]
        widgets = {
            'last_service_date': forms.DateInput(attrs={'type': 'date'}),
            'equipment_notes': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only offer drivers who have no ambulance yet (plus the current one on edit).
        # `ambulance` is the reverse OneToOne name, so ambulance__isnull=True
        # means "no ambulance points at this driver".
        free = Q(ambulance__isnull=True)
        if self.instance and self.instance.pk and self.instance.driver_id:
            # When editing, the ambulance's own driver must stay selectable.
            free |= Q(pk=self.instance.driver_id)
        self.fields['driver'].queryset = (
            DriverProfile.objects.filter(free).select_related('user').order_by('user__username')
        )

    # clean_<field> methods tidy a single field after the standard validation.
    def clean_ambulance_id(self):
        # Normalise so "amb-001 " and "AMB-001" cannot both exist.
        return self.cleaned_data['ambulance_id'].strip().upper()

    def clean_registration_number(self):
        return self.cleaned_data['registration_number'].strip().upper()

    def clean_last_service_date(self):
        date = self.cleaned_data.get('last_service_date')
        if date and date > datetime.date.today():
            raise forms.ValidationError("Last service date cannot be in the future.")
        return date

    def clean(self):
        """Cross-field rule: an ambulance on a trip must have somebody driving it."""
        cleaned = super().clean()
        if cleaned.get('status') == Ambulance.Status.ON_TRIP and not cleaned.get('driver'):
            self.add_error('driver', "An ambulance that is on a trip must have a driver assigned.")
        return cleaned


class AmbulanceStatusForm(forms.ModelForm):
    """Quick status change used by staff and by the assigned driver."""

    class Meta:
        model = Ambulance
        fields = ['status']

    def __init__(self, *args, allowed_statuses=None, **kwargs):
        super().__init__(*args, **kwargs)
        # Restrict the dropdown to the statuses this person may choose
        # (drivers get fewer options than staff - see DRIVER_ALLOWED_STATUSES in views.py).
        # None means "no restriction".
        if allowed_statuses is not None:
            self.fields['status'].choices = [
                (value, label) for value, label in Ambulance.Status.choices if value in allowed_statuses
            ]

    def clean_status(self):
        status = self.cleaned_data['status']
        if status == Ambulance.Status.ON_TRIP and not self.instance.driver_id:
            raise forms.ValidationError("Assign a driver before setting the ambulance on a trip.")
        return status
