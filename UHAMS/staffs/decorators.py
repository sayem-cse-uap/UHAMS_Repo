"""
staffs.decorators - view guards specific to the staff area.

They build on core.decorators.role_required: first make sure someone is logged
in AND is a STAFF user, then additionally check the StaffProfile.

Both decorators leave two attributes on the request for the view to use:
    request.uhams_user     - the logged-in User            (set by role_required)
    request.staff_profile  - that user's StaffProfile      (set here)
"""
from functools import wraps

from django.contrib import messages
from django.shortcuts import redirect

from core.decorators import role_required
from core.models import User
from .models import StaffProfile


def staff_profile_required(view_func):
    """Logged-in STAFF user who has a StaffProfile (any access level).
    Sets request.uhams_user and request.staff_profile."""
    @wraps(view_func)
    def inner(request, *args, **kwargs):
        # select_related("user") loads the User in the same query.
        profile = StaffProfile.objects.select_related("user").filter(user=request.uhams_user).first()
        if profile is None:
            # A STAFF-role account can exist without a profile (e.g. created via
            # the admin site). Such a user can log in but not use staff tools.
            messages.error(request, "Your account has no staff profile yet. Ask a manager to set one up.")
            return redirect("staffs:dashboard")
        request.staff_profile = profile
        return view_func(request, *args, **kwargs)

    # Order of checks: role_required runs FIRST (login + role == STAFF) and only
    # then calls `inner`, which is why request.uhams_user is already available there.
    return role_required(User.Role.STAFF)(inner)


def manager_required(view_func):
    """Logged-in STAFF user whose StaffProfile has a manager-level access_level.
    Sets request.uhams_user and request.staff_profile."""
    @wraps(view_func)
    def inner(request, *args, **kwargs):
        profile = StaffProfile.objects.select_related("user").filter(user=request.uhams_user).first()
        # is_manager is True for access_level "manager" or "admin".
        if profile is None or not profile.is_manager:
            messages.error(request, "Only managers can open that page.")
            return redirect("staffs:dashboard")
        request.staff_profile = profile
        return view_func(request, *args, **kwargs)

    return role_required(User.Role.STAFF)(inner)
