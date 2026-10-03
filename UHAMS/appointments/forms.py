"""appointments.forms - the two forms of the appointment flow:
the patient's REQUEST form and the doctor's CONFIRM form."""
from django import forms
from django.utils import timezone

from .models import Appointment


class AppointmentRequestForm(forms.Form):
    """Used by a patient to request an appointment with a doctor."""
    date = forms.DateField(
        label="Preferred date",
        widget=forms.DateInput(attrs={'type': 'date'}),   # browser date picker
    )
    reason = forms.CharField(
        label="Reason for visit",
        required=False,
        widget=forms.Textarea(attrs={'rows': 3}),
    )

    def clean_date(self):
        """A request cannot be for a day that has already passed (today is fine)."""
        date = self.cleaned_data['date']
        if date < timezone.localdate():
            raise forms.ValidationError("Please choose today or a future date.")
        return date


class _TimeBlockChoiceField(forms.ModelChoiceField):
    """Dropdown label such as 'Monday, 09:00 AM - 12:00 PM' for a TimeBlock."""
    def label_from_instance(self, block):
        return f"{block.get_day_display()}, {block.start_time:%I:%M %p} - {block.end_time:%I:%M %p}"


class AppointmentConfirmForm(forms.Form):
    """Used by a doctor to confirm a request and assign a time block from his schedule."""
    # queryset=None here; the real queryset (this doctor's blocks only) is set in __init__.
    time_block = _TimeBlockChoiceField(queryset=None, label="Time block")
    date = forms.DateField(
        label="Appointment date",
        widget=forms.DateInput(attrs={'type': 'date'}),
    )
    room_number = forms.CharField(max_length=10, required=False, label="Room number")

    def __init__(self, *args, appointment=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.appointment = appointment
        # The doctor can only choose among THEIR OWN time blocks.
        self.fields['time_block'].queryset = appointment.doctor.timeblock_set.order_by('day', 'start_time')

    def clean(self):
        """Three checks on the chosen block + date, applied in this order."""
        cleaned = super().clean()
        block = cleaned.get('time_block')
        date = cleaned.get('date')
        if block and date:
            if date < timezone.localdate():
                self.add_error('date', "The date cannot be in the past.")
            # isoweekday(): Monday=1 ... Sunday=7, the same numbers as TimeBlock.day.
            # So this verifies the chosen DATE falls on the block's weekday.
            elif date.isoweekday() != block.day:
                self.add_error(
                    'date',
                    f"{date:%d %b %Y} is a {date:%A}, but this time block is on {block.get_day_display()}.",
                )
            else:
                # Double-booking guard: is another confirmed/scheduled appointment already
                # using this doctor + block + date? (exclude() ignores the appointment being edited.)
                taken = Appointment.objects.filter(
                    doctor=self.appointment.doctor,
                    time_block=block,
                    date=date,
                    status__in=[Appointment.Status.CONFIRMED, Appointment.Status.SCHEDULED_WAITING],
                ).exclude(pk=self.appointment.pk).exists()
                if taken:
                    self.add_error('time_block', "This time block is already booked on that date.")
        return cleaned
