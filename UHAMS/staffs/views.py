from django.contrib import messages
from django.shortcuts import render, redirect

from appointments.models import Appointment
from core.decorators import role_required
from core.models import User
from doctors.models import DoctorProfile
from patients.models import PatientProfile
from .forms import StaffRegistrationForm
from .models import AmbulanceCall, StaffProfile


def register_staff(request):
    if request.method == 'POST':
        form = StaffRegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Staff member registered successfully!")
            return redirect('login')
    else:
        form = StaffRegistrationForm()

    return render(request, 'staffs-templates/register-staff.html', {'form': form})


@role_required(User.Role.STAFF)
def staff_dashboard(request):
    user = request.uhams_user
    context = {
        'my_profile': StaffProfile.objects.filter(user=user).first(),
        'appointments': Appointment.objects.select_related(
            'doctor__user', 'patient__user', 'time_block').order_by('-date', '-id'),
        'doctors': DoctorProfile.objects.select_related('user'),
        'patients': PatientProfile.objects.select_related('user', 'assigned_staff__user'),
        'staffs': StaffProfile.listAllStaff(),
        'ambulance_calls': AmbulanceCall.objects.select_related(
            'ambulance', 'handled_by__user')[:10],
    }
    return render(request, 'staffs-templates/staff-dashboard.html', context)
