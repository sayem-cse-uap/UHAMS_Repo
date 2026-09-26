from django.shortcuts import render, redirect
from django.contrib import messages

from core.context_processors import custom_login_required
from .forms import DoctorRegistrationForm

def register_doctor(request):
    if request.method == 'POST':
        form = DoctorRegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Doctor registered successfully!")
            return redirect('login')  # Redirect to your desired URL
        # test_text = "huh? this is not inside else block"
    else:
        form = DoctorRegistrationForm()
        # test_text = "can you see this? views.py inside staffs-templates app"

    return render(request, 'doctors-templates/register-doctor.html', {'form': form})

@custom_login_required
def doctor_dashboard(request):
    return render(request,'doctors-templates/doctor-dashboard.html')