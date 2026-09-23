from django.shortcuts import render, redirect
from django.contrib import messages

from core.context_processors import custom_login_required
from .forms import PatientRegistrationForm

def register_patient(request):
    if request.method == 'POST':
        form = PatientRegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Patient registered successfully!")
            return redirect('login')  # Redirect to your desired URL
        # test_text = "huh? this is not inside else block"
    else:
        form = PatientRegistrationForm()
        # test_text = "can you see this? views.py inside staffs-templates app"

    return render(request, 'patients-templates/register-patient.html', {'form': form})

@custom_login_required
def patient_dashboard(request):
    return render(request,'patients-templates/patient-dashboard.html')