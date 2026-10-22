"""
patients.views - what a patient can do: register, see their appointments and the
list of doctors, and request an appointment with a doctor.

APPOINTMENT FLOW (shared with the doctors app)
  1. Patient picks a doctor and sends a request with a preferred date + reason
     -> an Appointment is created with status PENDING_CONFIRMATION (this file).
  2. The doctor opens the request, picks one of their weekly time blocks and a
     date -> status becomes CONFIRMED (doctors/views.py -> confirm_appointment).
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages

from appointments.forms import AppointmentRequestForm
from appointments.models import Appointment
from core.decorators import role_required
from core.models import User
from doctors.models import DoctorProfile
from .forms import PatientRegistrationForm
from .models import PatientProfile

def register_patient(request):
    """Public sign-up page for patients. No login needed (a new patient has no account yet)."""
    if request.method == 'POST':
        form = PatientRegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Patient registered successfully!")
            return redirect('core:login')   # now they can log in
    else:
        form = PatientRegistrationForm()

    return render(request, 'patients-templates/register-patient.html', {'form': form})


@role_required(User.Role.PATIENT)
def patient_dashboard(request):
    """The patient's home page: their appointments, plus the doctors they can book.

    role_required only lets PATIENT accounts in (anyone else is sent to the home
    page with an error) and puts the user on request.uhams_user."""
    user = request.uhams_user

    patient = PatientProfile.objects.filter(user=user).first()
    # prefetch_related('timeblock_set') loads every doctor's schedule in ONE extra
    # query, so the template can list each doctor's time blocks without a query per doctor.
    doctors = DoctorProfile.objects.select_related('user').prefetch_related('timeblock_set').order_by('user__first_name', 'user__username')
    appointments = []
    if patient:
        appointments = (Appointment.objects.filter(patient=patient)
                        .select_related('doctor__user', 'time_block')
                        .order_by('-date', '-id'))
    return render(request, 'patients-templates/patient-dashboard.html', {
        'doctors': doctors,
        'appointments': appointments,
    })


@role_required(User.Role.PATIENT)
def book_appointment(request, doctor_id):
    """Request an appointment with one doctor (identified by `doctor_id` in the URL)."""
    user = request.uhams_user
    # A PATIENT account should have a PatientProfile; if it somehow does not, turn it away.
    patient = PatientProfile.objects.filter(user=user).first()
    if patient is None:
        messages.error(request, "Only patients can request appointments.")
        return redirect('patients:dashboard')

    doctor = get_object_or_404(DoctorProfile.objects.select_related('user'), pk=doctor_id)

    if request.method == 'POST':
        form = AppointmentRequestForm(request.POST)
        if form.is_valid():
            # The patient only chooses a preferred DATE. No time block / room yet:
            # the doctor assigns those when confirming.
            Appointment.objects.create(
                doctor=doctor,
                patient=patient,
                date=form.cleaned_data['date'],
                reason=form.cleaned_data['reason'],
                status=Appointment.Status.PENDING_CONFIRMATION,
            )
            messages.success(request, f"Your appointment request was sent to Dr. {doctor.user.get_full_name() or doctor.user.username}. You will see the assigned time here once it is confirmed.")
            return redirect('patients:dashboard')
    else:
        form = AppointmentRequestForm()

    return render(request, 'patients-templates/book-appointment.html', {
        'doctor': doctor,
        # Show the doctor's weekly schedule so the patient can pick a sensible date.
        'blocks': doctor.timeblock_set.order_by('day', 'start_time'),
        'form': form,
    })
