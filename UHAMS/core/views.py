from django.shortcuts import render, redirect

from .models import User

from core.forms import AccountForm, ChangePasswordForm, LoginForm
from core.security import password_matches
from core.decorators import role_required
from ambulances.models import Ambulance
from doctors.forms import DoctorSettingsForm
from doctors.models import DoctorProfile
from drivers.forms import DriverSettingsForm
from drivers.models import DriverProfile
from patients.forms import PatientSettingsForm
from patients.models import PatientProfile
from staffs.forms import StaffSettingsForm
from staffs.models import StaffProfile
from django.contrib import messages


def home(request):
    return render(request, 'home.html')

DASHBOARD_BY_ROLE = {
    User.Role.STAFF: 'staffs:dashboard',
    User.Role.DOCTOR: 'doctors:dashboard',
    User.Role.DRIVER: 'drivers:dashboard',
    User.Role.PATIENT: 'patients:dashboard',
}


def loginView(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']

            user = User.objects.filter(username=username, is_active=True).first()
            # One generic message so the form does not reveal which usernames exist.
            if user is None or not password_matches(user, password):
                form.add_error(None, 'Incorrect username or password.')
            else:
                request.session.cycle_key()  # new session id on login
                request.session['user_id'] = user.id
                return redirect(DASHBOARD_BY_ROLE.get(user.role, 'core:home'))
    else:
        form = LoginForm()

    return render(request, 'login.html', {'form': form})

def logoutView(request):
    # Completely destroy session data and cookies
    request.session.flush()
    messages.info(request, "You have been logged out.")
    return redirect('core:login')

def _role_profile(user):
    """Return (profile, settings_form_class, read_only_rows) for the user's role."""
    if user.role == User.Role.PATIENT:
        profile = PatientProfile.objects.select_related('assigned_staff__user').filter(user=user).first()
        rows = []
        if profile and profile.assigned_staff:
            staff = profile.assigned_staff
            rows.append(('Assigned staff member', staff.user.get_full_name() or staff.user.username))
        return profile, PatientSettingsForm, rows

    if user.role == User.Role.DOCTOR:
        profile = DoctorProfile.objects.filter(user=user).first()
        rows = [('License number', profile.licenseNumber)] if profile else []
        return profile, DoctorSettingsForm, rows

    if user.role == User.Role.DRIVER:
        profile = DriverProfile.objects.filter(user=user).first()
        rows = []
        if profile:
            ambulance = Ambulance.objects.filter(driver=profile).first()
            rows = [
                ('Driver license number', profile.driver_license_number),
                ('Assigned ambulance', f"{ambulance.ambulance_id} ({ambulance.get_status_display()})" if ambulance else 'None assigned yet'),
            ]
        return profile, DriverSettingsForm, rows

    if user.role == User.Role.STAFF:
        profile = StaffProfile.objects.filter(user=user).first()
        rows = []
        if profile:
            rows = [
                ('Job title', profile.title),
                ('Role', profile.get_role_display()),
                ('Department', profile.department),
                ('Access level', profile.get_access_level_display()),
                ('Salary', profile.salary),
                ('Current assignment', profile.current_assignment or 'None'),
            ]
        return profile, StaffSettingsForm, rows

    return None, None, []


@role_required()
def account_settings(request):
    user = request.uhams_user
    profile, profile_form_class, profile_rows = _role_profile(user)
    section = request.POST.get('section') if request.method == 'POST' else None

    account_form = AccountForm(request.POST if section == 'account' else None,
                               instance=user, prefix='account')
    password_form = ChangePasswordForm(user, request.POST if section == 'password' else None,
                                       prefix='password')
    profile_form = None
    if profile is not None:
        profile_form = profile_form_class(request.POST if section == 'profile' else None,
                                          instance=profile, prefix='profile')

    if request.method == 'POST':
        if section == 'account' and account_form.is_valid():
            account_form.save()
            messages.success(request, "Your account details were updated.")
            return redirect('core:settings')
        if section == 'profile' and profile_form is not None and profile_form.is_valid():
            profile_form.save()
            messages.success(request, "Your profile was updated.")
            return redirect('core:settings')
        if section == 'password' and password_form.is_valid():
            password_form.save()
            messages.success(request, "Your password was changed.")
            return redirect('core:settings')

    # Fresh copy for display: a failed ModelForm validation may have modified `user` in memory.
    return render(request, 'settings.html', {
        'account_user': User.objects.get(pk=user.pk),
        'account_form': account_form,
        'profile_form': profile_form,
        'profile_rows': profile_rows,
        'password_form': password_form,
    })


def register_new_user(request):
    return render(request, 'register.html')
