"""
core.decorators - "is someone logged in, and are they allowed here?"

A decorator wraps a view function with extra logic that runs BEFORE the view.
`@role_required(...)` placed above a view means: "only run this view if a user
is logged in (and has one of these roles); otherwise redirect them away".

The project does not use Django's `request.user` / `@login_required`. Login just
stores the user's id in the session under the key 'user_id' (see core/views.py
-> loginView), and the helpers below read it back.
"""
from functools import wraps

from django.contrib import messages
from django.shortcuts import redirect

from .models import User


def get_logged_in_user(request):
    """The project logs in through its own session key ('user_id').

    Returns the User object, or None when nobody is logged in (or the account
    has since been deactivated / deleted)."""
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    # is_active=True means a deactivated account is treated as logged out, even
    # if its old session cookie is still around.
    return User.objects.filter(id=user_id, is_active=True).first()


def role_required(*roles):
    """
    Require a logged-in user, optionally restricted to the given User.Role values.
    The user is made available as request.uhams_user.

    Usage:
        @role_required()                              # any logged-in user
        @role_required(User.Role.STAFF)               # staff only
        @role_required(User.Role.STAFF, User.Role.DRIVER)   # staff or drivers

    This is a "decorator factory": role_required(...) returns the real
    decorator, which in turn returns the wrapper that replaces the view.
    """
    def decorator(view_func):
        @wraps(view_func)   # keeps the original view's name/docstring on the wrapper
        def wrapper(request, *args, **kwargs):
            user = get_logged_in_user(request)
            if user is None:
                # Not logged in (or account disabled): wipe any stale session
                # data and send them to the login page.
                request.session.flush()
                return redirect("core:login")
            if roles and user.role not in roles:
                # Logged in, but the wrong kind of account for this page.
                messages.error(request, "You do not have permission to access that page.")
                return redirect("core:home")
            # Stash the user on the request so the view (and any decorator
            # that runs after this one, e.g. staffs.decorators) does not have
            # to look it up again.
            request.uhams_user = user
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator
