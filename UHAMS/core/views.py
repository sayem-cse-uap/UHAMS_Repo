from django.shortcuts import render, redirect

from staffs.forms import StaffRegistrationForm
from django.contrib import messages

# Create your views here.
def dashboard(request):
    return render(request,'dashboard.html')

def loginView(request):
    return render(request,'login.html')

# def logoutView(request):
#     return render(request,'logout.html')