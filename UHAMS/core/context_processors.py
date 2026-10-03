from functools import wraps

from django.shortcuts import redirect

from .models import User
def load_logged_in_user(request):
    user_id = request.session.get('user_id')
    if user_id:
        try:
            # Fetch the user using the custom session ID
            user = User.objects.get(id=user_id)
            is_manager = False
            if user.role == User.Role.STAFF:
                from staffs.models import StaffProfile  # local import avoids a circular import
                is_manager = StaffProfile.objects.filter(
                    user=user, access_level__in=list(StaffProfile.MANAGER_LEVELS)
                ).exists()
            return {'logged_in_user': user, 'is_staff_manager': is_manager}
        except User.DoesNotExist:
            pass

    return {'logged_in_user': None, 'is_staff_manager': False}

def custom_login_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if 'user_id' not in request.session:
            return redirect('login')  # Redirect to your login URL name
        return view_func(request, *args, **kwargs)
    return wrapper
