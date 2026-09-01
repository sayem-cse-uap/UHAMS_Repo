from django.shortcuts import render, redirect

from staffs.forms import StaffRegistrationForm
from django.contrib import messages

# Create your views here.
def home(request):
    return render(request,'home.html')