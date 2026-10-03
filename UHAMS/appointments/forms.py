from django import forms
from django.utils import timezone

from .models import Appointment


class AppointmentRequestForm(forms.Form):
    """Used by a patient to request an appointment with a doctor."""
    date = forms.DateField(
        label="Preferred date",
        widget=forms.DateInput(attrs={'type': 'date'}),
    )
    reason = forms.CharField(
        label="Reason for visit",
        required=False,
        widget=forms.Textarea(attrs={'rows': 3}),
    )

    def clean_date(self):
        date = self.cleaned_data['date']
        if date < timezone.localdate():
            raise forms.ValidationError("Please choose today or a future date.")
        return date


class _TimeBlockChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, block):
        return f"{block.get_day_display()}, {block.start_time:%I:%M %p} - {block.end_time:%I:%M %p}"


class AppointmentConfirmForm(forms.Form):
    """Used by a doctor to confirm a request and assign a time block from his schedule."""
    time_block = _TimeBlockChoiceField(queryset=None, label="Time block")
    date = forms.DateField(
        label="Appointment date",
        widget=forms.DateInput(attrs={'type': 'date'}),
    )
    room_number = forms.CharField(max_length=10, required=False, label="Room number")

    def __init__(self, *args, appointment=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.appointment = appointment
        self.fields['time_block'].queryset = appointment.doctor.timeblock_set.order_by('day', 'start_time')

    def clean(self):
        cleaned = super().clean()
        block = cleaned.get('time_block')
        date = cleaned.get('date')
        if block and date:
            if date < timezone.localdate():
                self.add_error('date', "The date cannot be in the past.")
            elif date.isoweekday() != block.day:
                self.add_error(
                    'date',
                    f"{date:%d %b %Y} is a {date:%A}, but this time block is on {block.get_day_display()}.",
                )
            else:
                taken = Appointment.objects.filter(
                    doctor=self.appointment.doctor,
                    time_block=block,
                    date=date,
                    status__in=[Appointment.Status.CONFIRMED, Appointment.Status.SCHEDULED_WAITING],
                ).exclude(pk=self.appointment.pk).exists()
                if taken:
                    self.add_error('time_block', "This time block is already booked on that date.")
        return cleaned
