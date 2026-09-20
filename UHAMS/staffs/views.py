from django.shortcuts import render, redirect
from django.contrib import messages

from core.context_processors import custom_login_required
from .forms import StaffRegistrationForm

def register_staff(request):
    if request.method == 'POST':
        form = StaffRegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Staff member registered successfully!")
            return redirect('login')  # Redirect to your desired URL
        # test_text = "huh? this is not inside else block"
    else:
        form = StaffRegistrationForm()
        # test_text = "can you see this? views.py inside staffs-templates app"

    return render(request, 'staffs-templates/register-staff.html', {'form': form})

@custom_login_required
def staff_dashboard(request):
    return render(request,'staffs-templates/staff-dashboard.html')