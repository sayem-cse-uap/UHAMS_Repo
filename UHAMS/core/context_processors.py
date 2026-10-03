"""
core.context_processors - variables that are available in EVERY template.

Registered in settings.TEMPLATES -> OPTIONS -> context_processors. Django calls
`load_logged_in_user(request)` while rendering every page and merges the
returned dict into that page's context. That is why base.html can simply write
{% if logged_in_user %} without any view having to pass it in.
"""
from functools import wraps

from django.shortcuts import redirect

from .models import User


def load_logged_in_user(request):
    """Return {'logged_in_user': <User or None>, 'is_staff_manager': <bool>} for templates.

    * logged_in_user  - used by base.html to decide between the signed-in layout
                        (sidebar) and the public layout, and which menu to show.
    * is_staff_manager - True for staff whose access level is manager/admin;
                        base.html uses it to show the "Manage staff" menu items.
    """
    user_id = request.session.get('user_id')
    if user_id:
        try:
            # Fetch the user using the custom session ID
            user = User.objects.get(id=user_id)
            is_manager = False
            if user.role == User.Role.STAFF:
                from staffs.models import StaffProfile  # local import avoids a circular import
                # Is there a staff profile for this user with a manager-level
                # access_level? (MANAGER_LEVELS = {'manager', 'admin'})
                is_manager = StaffProfile.objects.filter(
                    user=user, access_level__in=list(StaffProfile.MANAGER_LEVELS)
                ).exists()
            return {'logged_in_user': user, 'is_staff_manager': is_manager}
        except User.DoesNotExist:
            # The session points at a user that no longer exists: behave as
            # logged out instead of crashing.
            pass

    return {'logged_in_user': None, 'is_staff_manager': False}


def custom_login_required(view_func):
    """Minimal "must be logged in" decorator (no role check).

    Only checks that the session has a 'user_id'; the doctors, patients and
    drivers views use it and then do their own role/profile checks inside the
    view. (core.decorators.role_required is the stricter, newer alternative.)
    It lives in this module for historical reasons, which is why it is imported
    as `from core.context_processors import custom_login_required` elsewhere.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if 'user_id' not in request.session:
            return redirect('core:login')
        return view_func(request, *args, **kwargs)
    return wrapper
