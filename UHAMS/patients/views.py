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
from core.context_processors import custom_login_required
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


def _current_user(request):
    """The logged-in User (looked up from the session's 'user_id'), or None."""
    return User.objects.filter(id=request.session.get('user_id')).first()


def _role_redirect(user):
    """The login view sends every role to the patient dashboard, so send others where they belong."""
    # (Login now sends each role to its own dashboard - core.views.DASHBOARD_BY_ROLE -
    # but this guard is still useful if a doctor/staff/driver types the patient URL by hand.)
    target = {
        User.Role.DOCTOR: 'doctors:dashboard',
        User.Role.STAFF: 'staffs:dashboard',
        User.Role.DRIVER: 'drivers:dashboard',
    }.get(user.role)
    # PATIENT is not in the dictionary, so .get() returns None -> no redirect.
    return redirect(target) if target else None


@custom_login_required
def patient_dashboard(request):
    """The patient's home page: their appointments, plus the doctors they can book."""
    user = _current_user(request)
    if user is None:
        return redirect('core:login')
    other = _role_redirect(user)
    if other:
        return other

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


@custom_login_required
def book_appointment(request, doctor_id):
    """Request an appointment with one doctor (identified by `doctor_id` in the URL)."""
    user = _current_user(request)
    # Only someone who has a PatientProfile may book; everyone else is turned away.
    patient = PatientProfile.objects.filter(user=user).first() if user else None
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
