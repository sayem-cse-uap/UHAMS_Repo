from django.shortcuts import render, redirect
from django.contrib import messages
from .forms import StaffRegistrationForm

# Create your views here.
# def register_staff(request):
#     if request.method == 'POST':
#         form = StaffRegistrationForm(request.POST)
#         if form.is_valid():
#             form.save()
#             messages.success(request, "Staff member registered successfully!")
#             return redirect('home')  # Redirect to your desired URL
#         test_text = "huh? this is not inside else block"
#     else:
#         form = StaffRegistrationForm()
#         test_text = "can you see this? views.py inside staffs app"
#
#     return render(request, 'register-staff.html', {'form': form, 'test_text': test_text})