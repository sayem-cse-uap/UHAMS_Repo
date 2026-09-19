from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.shortcuts import render, redirect

from staffs.forms import StaffRegistrationForm
from django.contrib import messages

# Create your views here.
@login_required
def dashboard(request):
    return render(request,'dashboard.html')


def loginView(request):
    if request.method == 'POST':
        # 1. Bind POST data to Django's built-in AuthenticationForm
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            # 2. Get the authenticated user object and start the session
            user = form.get_user()
            login(request, user)

            # 3. Redirect to destination (or fallback page)
            next_url = request.GET.get('next', 'dashboard')
            return redirect(next_url)
    else:
        # 4. Instantiate an empty form for GET requests
        form = AuthenticationForm()

    # 5. Pass the form to your template via context
    return render(request, 'login.html', {'form': form})


# def loginView(request):
#     return render(request,'login.html')

# def logoutView(request):
#     return render(request,'logout.html')