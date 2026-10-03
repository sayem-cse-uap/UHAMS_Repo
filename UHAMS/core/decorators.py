from functools import wraps

from django.contrib import messages
from django.shortcuts import redirect

from .models import User


def get_logged_in_user(request):
    """The project logs in through its own session key ('user_id')."""
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    return User.objects.filter(id=user_id, is_active=True).first()


def role_required(*roles):
    """
    Require a logged-in user, optionally restricted to the given User.Role values.
    The user is made available as request.uhams_user.
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            user = get_logged_in_user(request)
            if user is None:
                request.session.flush()
                return redirect("login")
            if roles and user.role not in roles:
                messages.error(request, "You do not have permission to access that page.")
                return redirect("home")
            request.uhams_user = user
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator
