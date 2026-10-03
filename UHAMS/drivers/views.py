"""drivers.views - driver registration and the driver's dashboard."""
from django.shortcuts import render, redirect
from django.contrib import messages

from core.context_processors import custom_login_required
from .forms import DriverRegistrationForm

def register_driver(request):
    """Public sign-up page for drivers."""
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
    """The dashboard needs no data from the view: the template reaches everything
    through `logged_in_user.driverprofile.ambulance` (and its active call)."""
    return render(request,'drivers-templates/driver-dashboard.html')
