from django.shortcuts import render, redirect
from django.contrib import messages

from core.context_processors import custom_login_required
from .forms import DriverRegistrationForm

def register_driver(request):
    if request.method == 'POST':
        form = DriverRegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Driver registered successfully!")
            return redirect('core:login')
    else:
        form = DriverRegistrationForm()

    return render(request, 'drivers-templates/register-driver.html', {'form': form})

@custom_login_required
def driver_dashboard(request):
    return render(request,'drivers-templates/driver-dashboard.html')