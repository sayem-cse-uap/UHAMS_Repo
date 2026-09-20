from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.shortcuts import render, redirect

from .context_processors import custom_login_required
from .models import User
from django.contrib.auth.hashers import check_password

from core.forms import LoginForm
from staffs.forms import StaffRegistrationForm
from django.contrib import messages

from functools import wraps


# Usage in views.py:
# @custom_login_required


# Create your views here.
# @login_required
def home(request):
    return render(request, 'home.html')

def loginView(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']

            try:
                # Look up the user in your Core table
                user = User.objects.get(username=username)

                # Check password (use check_password if hashed, or direct comparison if plain text)
                if check_password(password, user.password) or user.password == password:
                    request.session['user_id'] = user.id
                    return redirect('staff-dashboard')
                else:
                    form.add_error('password', 'Incorrect password.')

            except User.DoesNotExist:
                form.add_error('username', 'User does not exist.')
    else:
        form = LoginForm()

    return render(request, 'login.html', {'form': form})

def logoutView(request):
    # Completely destroy session data and cookies
    request.session.flush()
    messages.info(request, "You have been logged out.")
    return redirect('login')

def register_new_user(request):
    return render(request, 'register.html')

# def loginView(request):
#     if request.method == 'POST':
#         # 1. Bind POST data to Django's built-in AuthenticationForm
#         form = AuthenticationForm(request, data=request.POST)
#         if form.is_valid():
#             # 2. Get the authenticated user object and start the session
#             user = form.get_user()
#             login(request, user)
#
#             # 3. Redirect to destination (or fallback page)
#             next_url = request.GET.get('next', 'dashboard')
#             return redirect(next_url)
#     else:
#         # 4. Instantiate an empty form for GET requests
#         form = AuthenticationForm()
#
#     # 5. Pass the form to your template via context
#     return render(request, 'login.html', {'form': form})




# def logoutView(request):
#     return render(request,'logout.html')