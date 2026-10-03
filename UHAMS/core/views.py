"""
core.views - the pages that do not belong to one specific role.

  home                 landing page
  loginView            log in and send the user to the right dashboard
  logoutView           log out
  register_new_user    "which account type do you want?" chooser
  account_settings     the Settings page (account details + role profile + password)

HOW LOGIN WORKS IN THIS PROJECT
-------------------------------
Django ships with a ready-made login system (django.contrib.auth.login), but
this project does not use it. Instead:

  1. loginView checks the username/password itself.
  2. On success it stores the user's database id in the session:
         request.session['user_id'] = user.id
  3. Every protected view then reads that id back (core/decorators.py and
     core/context_processors.py) to find out who is making the request.
  4. Logging out just empties the session.

The session itself is a server-side record identified by a random cookie, so
the browser never holds anything it could tamper with except that random id.
"""
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
    """Landing page. The template shows different buttons depending on whether
    the visitor is logged in (it reads `logged_in_user` from the context processor)."""
    return render(request, 'home.html')

# Where each kind of user lands right after logging in. The values are URL
# names ('<app namespace>:<url name>') that redirect() resolves into real paths.
DASHBOARD_BY_ROLE = {
    User.Role.STAFF: 'staffs:dashboard',
    User.Role.DOCTOR: 'doctors:dashboard',
    User.Role.DRIVER: 'drivers:dashboard',
    User.Role.PATIENT: 'patients:dashboard',
}


def loginView(request):
    """Show the login form (GET) and process it (POST)."""
    if request.method == 'POST':
        # Bind the submitted data to the form and validate the basic shape
        # (both fields present). This does NOT check the password yet.
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']

            # Look the user up by name; only active accounts may log in.
            user = User.objects.filter(username=username, is_active=True).first()
            # One generic message so the form does not reveal which usernames exist.
            # (Same text whether the username is unknown or the password is wrong.)
            if user is None or not password_matches(user, password):
                # add_error(None, ...) attaches a form-wide ("non-field") error.
                form.add_error(None, 'Incorrect username or password.')
            else:
                # cycle_key() gives the session a brand-new id while keeping its
                # data. This defeats "session fixation" (an attacker planting a
                # known session id before the victim logs in).
                request.session.cycle_key()  # new session id on login
                request.session['user_id'] = user.id   # <- this line IS "being logged in"
                return redirect(DASHBOARD_BY_ROLE.get(user.role, 'core:home'))
    else:
        # GET request: show an empty form.
        form = LoginForm()

    # Reached on GET, or on POST with errors (the form then shows them).
    return render(request, 'login.html', {'form': form})

def logoutView(request):
    """Log out: destroy the session and go back to the login page."""
    # Completely destroy session data and cookies
    # flush() deletes the server-side session record and issues a fresh empty
    # one, so 'user_id' (and everything else) is gone.
    request.session.flush()
    messages.info(request, "You have been logged out.")
    return redirect('core:login')

def _role_profile(user):
    """Return (profile, settings_form_class, read_only_rows) for the user's role.

    The Settings page is shared by all four roles but each role has different
    extra details. This helper hides that difference and returns three things:

      profile            - the role's profile row (PatientProfile, DoctorProfile, ...)
                           or None if the account has no profile yet
      settings_form_class- the ModelForm class that edits the editable part of it
      read_only_rows     - list of (label, value) pairs shown as a plain table for
                           things the user may SEE but not change (license number,
                           salary, access level, ...)
    """
    if user.role == User.Role.PATIENT:
        # select_related('assigned_staff__user') fetches the staff member and
        # their user in the same SQL query, avoiding extra queries later.
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
            # The ambulance is found from the Ambulance side (Ambulance.driver
            # points at the driver profile).
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
            # Everything here is read-only: only a manager may change these
            # (see staffs/views.py -> manage_staff_detail).
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


@role_required()   # any logged-in user, whatever the role
def account_settings(request):
    """The Settings page. It contains THREE independent forms on one page:

        section=account  -> name, email, phone        (AccountForm)
        section=profile  -> role-specific details     (the role's SettingsForm)
        section=password -> change password           (ChangePasswordForm)

    Each form's <form> in settings.html carries a hidden field called "section".
    On POST, that value tells us which of the three was actually submitted, so
    only that one is bound to the submitted data and saved; the other two are
    shown unbound. Each form also has a `prefix` so their input names
    (account-email, profile-bloodGroup, ...) never collide.
    """
    user = request.uhams_user
    profile, profile_form_class, profile_rows = _role_profile(user)
    section = request.POST.get('section') if request.method == 'POST' else None

    # Passing None as the data makes a form "unbound" (just displays current values).
    account_form = AccountForm(request.POST if section == 'account' else None,
                               instance=user, prefix='account')
    password_form = ChangePasswordForm(user, request.POST if section == 'password' else None,
                                       prefix='password')
    profile_form = None
    if profile is not None:
        profile_form = profile_form_class(request.POST if section == 'profile' else None,
                                          instance=profile, prefix='profile')

    if request.method == 'POST':
        # Post/Redirect/Get: after a successful save we redirect back to the
        # page, so pressing F5 does not resubmit the form.
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
        # If validation failed we fall through and re-render the page; the
        # submitted form then displays its error messages.

    # Fresh copy for display: a failed ModelForm validation may have modified `user` in memory.
    # (ModelForm validation writes the posted values onto the `instance` even
    # when they turn out to be invalid. Re-reading from the database means the
    # header of the page keeps showing the real, saved values.)
    return render(request, 'settings.html', {
        'account_user': User.objects.get(pk=user.pk),
        'account_form': account_form,
        'profile_form': profile_form,
        'profile_rows': profile_rows,
        'password_form': password_form,
    })


def register_new_user(request):
    """Public page that lists the account types you can register
    (patient / doctor / driver; staff only if you are a manager).
    The actual registration forms live in each role's own app."""
    return render(request, 'register.html')
