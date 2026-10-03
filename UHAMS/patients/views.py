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
    if request.method == 'POST':
        form = PatientRegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Patient registered successfully!")
            return redirect('core:login')
    else:
        form = PatientRegistrationForm()

    return render(request, 'patients-templates/register-patient.html', {'form': form})


def _current_user(request):
    return User.objects.filter(id=request.session.get('user_id')).first()


def _role_redirect(user):
    """The login view sends every role to the patient dashboard, so send others where they belong."""
    target = {
        User.Role.DOCTOR: 'doctors:dashboard',
        User.Role.STAFF: 'staffs:dashboard',
        User.Role.DRIVER: 'drivers:dashboard',
    }.get(user.role)
    return redirect(target) if target else None


@custom_login_required
def patient_dashboard(request):
    user = _current_user(request)
    if user is None:
        return redirect('core:login')
    other = _role_redirect(user)
    if other:
        return other

    patient = PatientProfile.objects.filter(user=user).first()
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
    user = _current_user(request)
    patient = PatientProfile.objects.filter(user=user).first() if user else None
    if patient is None:
        messages.error(request, "Only patients can request appointments.")
        return redirect('patients:dashboard')

    doctor = get_object_or_404(DoctorProfile.objects.select_related('user'), pk=doctor_id)

    if request.method == 'POST':
        form = AppointmentRequestForm(request.POST)
        if form.is_valid():
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
        'blocks': doctor.timeblock_set.order_by('day', 'start_time'),
        'form': form,
    })
