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
        profile = StaffProfile.objects.select_related("user").filter(user=request.uhams_user).first()
        if profile is None:
            messages.error(request, "Your account has no staff profile yet. Ask a manager to set one up.")
            return redirect("staffs:dashboard")
        request.staff_profile = profile
        return view_func(request, *args, **kwargs)

    return role_required(User.Role.STAFF)(inner)


def manager_required(view_func):
    """Logged-in STAFF user whose StaffProfile has a manager-level access_level.
    Sets request.uhams_user and request.staff_profile."""
    @wraps(view_func)
    def inner(request, *args, **kwargs):
        profile = StaffProfile.objects.select_related("user").filter(user=request.uhams_user).first()
        if profile is None or not profile.is_manager:
            messages.error(request, "Only managers can open that page.")
            return redirect("staffs:dashboard")
        request.staff_profile = profile
        return view_func(request, *args, **kwargs)

    return role_required(User.Role.STAFF)(inner)
