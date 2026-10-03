from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone

from appointments.forms import AppointmentConfirmForm
from appointments.models import Appointment
from core.context_processors import custom_login_required
from core.models import User
from .forms import DoctorRegistrationForm, TimeBlockForm
from .models import DoctorProfile

def register_doctor(request):
    if request.method == 'POST':
        form = DoctorRegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Doctor registered successfully!")
            return redirect('core:login')
    else:
        form = DoctorRegistrationForm()

    return render(request, 'doctors-templates/register-doctor.html', {'form': form})


def _current_doctor(request):
    """Return the DoctorProfile of the logged-in (session) user, or None."""
    user = User.objects.filter(id=request.session.get('user_id')).first()
    if user is None:
        return None
    return DoctorProfile.objects.filter(user=user).first()


@custom_login_required
def doctor_dashboard(request):
    doctor = _current_doctor(request)
    if doctor is None:
        messages.error(request, "Only doctors can open the doctor dashboard.")
        return redirect('patients:dashboard')

    base = Appointment.objects.filter(doctor=doctor).select_related('patient__user', 'time_block')
    pending = base.filter(status=Appointment.Status.PENDING_CONFIRMATION).order_by('date', 'id')
    confirmed = base.exclude(status=Appointment.Status.PENDING_CONFIRMATION).order_by('date', 'time_block__start_time')
    return render(request, 'doctors-templates/doctor-dashboard.html', {
        'doctor': doctor,
        'pending_appointments': pending,
        'confirmed_appointments': confirmed,
    })


@custom_login_required
def doctor_schedule(request):
    doctor = _current_doctor(request)
    if doctor is None:
        messages.error(request, "Only doctors can manage a schedule.")
        return redirect('patients:dashboard')

    if request.method == 'POST':
        form = TimeBlockForm(request.POST, doctor=doctor)
        if form.is_valid():
            block = form.save(commit=False)
            block.doctor = doctor
            block.save()
            messages.success(request, "Time block added to your schedule.")
            return redirect('doctors:schedule')
    else:
        form = TimeBlockForm(doctor=doctor)

    blocks = doctor.timeblock_set.order_by('day', 'start_time')
    return render(request, 'doctors-templates/doctor-schedule.html', {
        'doctor': doctor,
        'form': form,
        'blocks': blocks,
    })


@custom_login_required
def confirm_appointment(request, appointment_id):
    doctor = _current_doctor(request)
    if doctor is None:
        messages.error(request, "Only doctors can confirm appointments.")
        return redirect('patients:dashboard')

    appointment = get_object_or_404(Appointment, pk=appointment_id, doctor=doctor)
    if appointment.status != Appointment.Status.PENDING_CONFIRMATION:
        messages.info(request, "This appointment has already been confirmed.")
        return redirect('doctors:dashboard')

    if not doctor.timeblock_set.exists():
        messages.error(request, "Add at least one time block to your schedule before confirming.")
        return redirect('doctors:schedule')

    if request.method == 'POST':
        form = AppointmentConfirmForm(request.POST, appointment=appointment)
        if form.is_valid():
            appointment.time_block = form.cleaned_data['time_block']
            appointment.date = form.cleaned_data['date']
            if form.cleaned_data['room_number']:
                appointment.room_number = form.cleaned_data['room_number']
            appointment.status = Appointment.Status.CONFIRMED
            appointment.save()
            messages.success(request, "Appointment confirmed and time assigned.")
            return redirect('doctors:dashboard')
    else:
        form = AppointmentConfirmForm(
            appointment=appointment,
            initial={'date': appointment.date if appointment.date >= timezone.localdate() else None},
        )

    return render(request, 'doctors-templates/confirm-appointment.html', {
        'appointment': appointment,
        'form': form,
    })
